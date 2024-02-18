from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    

    def __str__(self):
        return f"Item #{self.name} {self.price}$"

class DiscountCode(models.Model):
    code = models.CharField(max_length=100, unique=True)
    discount_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"<{self.code}, {self.used}, {self.timestamp.isoformat()}>"