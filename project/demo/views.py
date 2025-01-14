from django.shortcuts import render

# Create your views here.
import random
import time

from django.db import transaction
from django.http import HttpRequest, HttpResponse
# Only because this is a quick and simple demo
from django.views.decorators.csrf import csrf_exempt

from .models import Item, DiscountCode



def validate_code(code: str) -> bool:
    try:
        discount = DiscountCode.objects.get(code=code)
        if not discount.used:
            return True
            print(f"The f{discount.code} used.")
    except DiscountCode.DoesNotExist: 
        pass
    
    return False

@csrf_exempt
def atomic_long_delay(request: HttpRequest) -> HttpResponse:
    """
    In this example, we:
        - Use an atomic code block
        - Introduce a long (possibly random) time gap between when we read
        v/s when we commit the transaction (end of the atomic code block).
        - Don't use row locking.

    In this case if we have more than 1 (sync) gunicorn worker running and
    the frequency of requests to this endpoint (or any endpoint modifying the
    account price) is greater than the time it takes for the atomic code
    block to run, then we can expect race conditions to occur.

    Typically, these kinds of things won't be found in development (unless you
    have really experienced dev teams with good code review skills).

    Note: We are not using using F() expressions due to complexities in the
    business logic. The random_delay represents processing the data related
    to the account and the request. During this time, we really don't want
    anything else to be using the account data (due to the risk of reading
    stale data).
    """
    try:
        item_name = request.POST["item"]
        code = request.POST["code"]
        if not item_name or not code:
            raise ValueError("Invalid item_name or code")

    except (KeyError, ValueError):
        return HttpResponse(status=400)

    if validate_code(code):
        with transaction.atomic():
            try:
                # Possibly reading stale data:
                item = Item.objects.get(name=item_name)
                discount = DiscountCode.objects.get(code=code)
            except Item.DoesNotExist:
                return HttpResponse(status=404)
            # Enough time for another request to be made or for the data read to
            # become stale:
            time.sleep(6)
            item.price -= discount.discount_percentage
            discount.used = True  
            discount.save()
            item.save()
    item = Item.objects.get(name=item_name)
    print(f"Item price: {item.price}")
    return HttpResponse(200)
    


@csrf_exempt
def non_atomic_long_delay(request: HttpRequest) -> HttpResponse:
    """
    This is more or less the same as atomic_long_delay. The only difference is
    that now the delay is between when we read v/s when we write instead of
    when we read v/s when we commit the transaction.
    
    In both of these examples we write at the very end of the transaction, so
    really, both of these functions are the exact same. I want to show that
    atomic transactions the real issue here - it's the delay b/w read and save.
    """
    try:
        item_name = request.POST["item"]
        code = request.POST["code"]
        if not item_name or not code:
            raise ValueError("Invalid item_name or code")

    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = Item.objects.get(name=item_name)
        discount = DiscountCode.objects.get(code=code)
    except Item.DoesNotExist:
        return HttpResponse(status=404)
    if validate_code(code):
        time.sleep(6)
        item.price -= discount.discount_percentage
        discount.used = True  
        discount.save()
        item.save()
    
    item = Item.objects.get(name=item_name)
    print(f"Item price: {item.price}")
    return HttpResponse(200)


@csrf_exempt
def atomic_no_delay(request: HttpRequest) -> HttpResponse:
    """
    Due to the absence of a large delay, the window for the race condition to
    occur is considerably reduced and you would need the request frequency to
    be much higher (and with more gunicorn workers to handle them in parallel)
    for a race condition to be triggered.

    Race conditions are now unlikely to occur but still very much possible.
    
    If you're only using 1 sync gunicorn worker then race conditions are not
    possible just like in the atomic_long_delay example; but you'll have
    terrible throughput and most requests would probably time out during high
    load.
    """
    try:
        item_name = request.POST["item"]
        code = request.POST["code"]
        if not item_name or not code:
            raise ValueError("Invalid item_name or code")

    except (KeyError, ValueError):
        return HttpResponse(status=400)
    
    if validate_code(code):
        with transaction.atomic():
            try:
                item = Item.objects.get(name=item_name)
                discount = DiscountCode.objects.get(code=code)
            except Item.DoesNotExist:
                return HttpResponse(status=404)
            
            item.price -= discount.discount_percentage
            discount.used = True  
            discount.save()
            item.save()

    item = Item.objects.get(name=item_name)
    print(f"Item price: {item.price}")
    return HttpResponse(200)


@csrf_exempt
def non_atomic_no_delay(request: HttpRequest) -> HttpResponse:
    """
    Effectively the same as atomic_no_delay. Just like how atomic_long_delay
    and non_atomic_long_delay are effectively the same.
    """
    try:
        item_name = request.POST["item"]
        code = request.POST["code"]
        if not item_name or not code:
            raise ValueError("Invalid item_name or code")

    except (KeyError, ValueError):
        return HttpResponse(status=400)
    
    if validate_code(code):
        try:
            item = Item.objects.get(name=item_name)
            discount = DiscountCode.objects.get(code=code)
        except Item.DoesNotExist:
            return HttpResponse(status=404)
        
        item.price -= discount.discount_percentage
        discount.used = True  
        discount.save()
        item.save()

    item = Item.objects.get(name=item_name)
    print(f"Item price: {item.price}")
    return HttpResponse(200)


@csrf_exempt
def row_locking_atomic_long_delay(request: HttpRequest) -> HttpResponse:
    """
    Here we demonstrate that even if we did have a long delay between when we
    read v/s when we commit the transaction, if we lock the row we are
    operating on, then race conditions will never occur.

    This isn't a silver bullet since by locking the row we're preventing every
    other endpoint depending on it from working (even the read-only endpoints).
    This could cause serious issues if the row is needed in multiple endpoints.

    select_for_update cannot be used outside of an SQL transaction (so atomic
    is necessary).

    Race conditions are now impossible.
    """
    try:
        item_name = request.POST["item"]
        code = request.POST["code"]
        if not item_name or not code:
            raise ValueError("Invalid item_name or code")

    except (KeyError, ValueError):
        return HttpResponse(status=400)

    if validate_code(code):
        with transaction.atomic():
            try:
                item = Item.objects.select_for_update().get(name=item_name)
                discount = DiscountCode.objects.get(code=code)
            except Item.DoesNotExist:
                return HttpResponse(status=404)
            time.sleep(6)
            item.price -= discount.discount_percentage
            discount.used = True  
            discount.save()
            item.save()

    item = Item.objects.get(name=item_name)
    print(f"Item price: {item.price}")
    return HttpResponse(200)
