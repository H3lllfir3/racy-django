# Racy Django - Demonstrating Race Conditions in Django
> Race Condition:  
A situation where two or more operations are attempted to be done concurrently
and the order of execution (and thus completion) of these operations is
non-deterministic. The result of this "race" between operations could lead to
incorrect results - such as one operation overwritting the results of another.

> This project is fork from [racy django](https://github.com/Hypro999/racy-django) 
> In the main project, the developer attempted to create a situation where a race condition occurs. In this fork, I have attempted to simulate this same situation using the HTTP/2 protocol.


## Django causes race conditions?!
NO. The actual problem lies at a more fundamental level - concurrent
execution involving a shared entity. Django's not to blame here. Django
actually makes it easy to avoid this if you try. But you have to know what
can happen, why it can happen, and when it's possible.

I'm choosing to explain how this can happen in an API written in Django because
of a particularly scarring incident I faced in my sophomore year of college
when developing and deploying the backend for an e-wallet/store kind of app.
This was before doing courses in OS, DBMS, etc. and before I seriously read
about concurrency and parallelism and stuff.

Everything was working fine in development, then weird issues started popping
up in production and no one could figure out why. It felt like being hit by a
truck.


## So what *is* causing race conditions then?
1. How many concurrent instances of your app are running (they don't
necessarily have to be parallel - watch Rob Pike's talk titled "Concurrency
is not Parallelism" to understand the difference). So for example, how many
Gunicorn workers are running and if they are sync or async workers.

2. If you're using any kinds of special countermeasures such as row locking.

These two factors decide if race conditions are even possible.

3. How much time there is between when your code reads data from a common
source (like a database) and when it writes it back.

4. How frequent the requests are.

These factors decide how often the latent race conditions could cause issues.

This project serves as a laboratory where we can demonstrate how these factors
can cause race conditions and how we can avoid them.


## About this project
It's a laboratory where we can see what's happening and play around with the
factors affecting race conditions.

### The (dockerized) application architecture:
- A Django project (unimaginatively named "project") with 1 application (named
demo) containing the code for the API. It will use Gunicorn as a WSGI server
with synchronous workers (3 by default) (in the "app" container).

- MySQL as the database (in the "db" container).

- Nginx as the front facing web server, serving static content directly and
proxy passing to Gunicorn for requests to the API (in the "server" container).

- A docker-compose file for orchestrating all of these containerized services.

- A tool for sending concurrent requests (meant to be used from the host).

### About the Django app:
It has 2 models:
1. Account - each account has a "balance".

2. Transaction - not to be confused with a database transaction; this
represents adding to the balance of the account. Each transaction has an
"amount" and is linked to an account (via. a "Foreign Key").

It has 5 API endpoints/views, all to accomplish the same thing - increase the
balance of an account and record this increment as a transaction.

Each view demonstrates a different way we could write code to acheive this,
and how some ways would lead to race conditions. Some endpoints have a shorter
window for race conditions to occur, some have a huge window, and one
completely prevents race conditions from occuring.

Look at the source code in `project/demo/views.py` to see what each endpoint
does, if it leads to race conditions, how, and why. It's better to keep the
code and the explanation next to each other in this case.


## Setup in 5 steps
1. Install the dependencies:
    - Git
    - Docker
    - Docker Compose
    - That's it....
    - [Optionally] A compiler for Go

2. Clone this repo:  
`git clone https://github.com/Hypro999/racy-django.git`

3. Start the django application using docker compose:  
```
cd racy-django
docker-compose up -d
```

4. Attach to the application container and create a superuser.  
The way you do this depends on how you have Docker installed.

If you use a GUI for Docker like:
    - VSCode with the Docker extension
    - The Docker Desktop Dashboard
    - etc.
then you should be able to easily figure it out yourself.

If you use a CLI, then as long as you only have one instance of this demo
running:  
```
docker exec -it racy_app_1 /bin/bash
```
If you have more than 1 instance running then you'll need to change the name
of the container from `racy_app_1` (the default) to whatever it is on your
system.

Once you've got a shell on the application container, run:  
```
python manage.py createsuperuser
```
and follow the steps. What I usually do is set the username to `admin`, skip
the email (just hit enter), then enter a lame password like `admin` or `pass`
or whatever since I'm just testing.

5. Go to the admin page at `http://localhost/admin/` > `Accounts` > `Add Accout`
and create a new account with a balance of 0. You'll want to come back to the
admin page to reset the balance and delete transactions when trying out
different things.

6. Once you're done playing around, run `docker-compose down` to stop these
services.


## How to use the concurrent request tool
It's written in Go but I've included precompiled binaries for linux/amd64 and
windows/amd64. For other platforms, you'll need to compile the tool yourself.
It will make 10 concurrent requests.

Usage:
```
tools/bin/make_requests[.exe] [-target target_name] [-wait wait_time]
```
where target_name is one of:
- atomic_long_delay
- non_atomic_long_delay
- atomic_no_delay
- non_atomic_no_delay
- row_locking_atomic_long_delay
and the wait_time is the number of seconds to wait in between requests
(by default it's 1).

e.g. `tools\bin\make_requests.exe -target row_locking_atomic_long_delay`


## How to change the factors affecting race conditions (in this project):
1. Number of concurrent instances of the app:  
Increase the number of gunicorn workers. Open up `config/django.env` and change
the value of the GUNICORN_WORKERS variable. Setting it to 1 will lead to no
race conditions since these are sync workers. Setting it to a higher value will
lead to more overwritting changes made to an account's balance if race
conditions were possible.  
e.g. with 3 workers and -wait=0 when using make_requests to contact
atomic_long_delay, you could expect every batch of 3 concurrent requests to
result in overwriting each other's changes made to balance (due to the present
race condition).  
Thus only around 1/3 of the requests would result in actually increasing the
balance. All transactions would be still recorded though, since we're always
making a new one and not modifying existing ones (the database handles race
conditions at this level, not us at the web application level).  
Restart the docker containers with `docker-compose restart` for the changes to
take effect (or just restart the `racy_app_1` container individually).

2. Usage of special counter measures (row locking):  
Use a different endpoint via. the -target flag with the make_requests tool.
The row_locking_atomic_long_delay endpoint is the only endpoint which will be
resilient to race conditions regardless of the number of gunicorn workers or
the frequency of requests. You might see some timed out requests though...

3. Delay between reading and writing/committing:  
Use a different endpoint via. the -target flag with the make_requests tool.
The *_no_delay endpoints generally don't show race conditions since the window
of time for them to occur is pretty small. You'd need a high number of parallel
instances and a high frequency of requesting to observe any. Most Django app
code I've seen (practically all of it actually...) is written like the
*_no_delay endpoints. Finally, the *_long_delay endpoints will easily show race
conditions if there are more than 1 gunicorn workers.

4. Frequency of requesting:  
Use the -wait flag with the make_requests tool. Increase it or decrease it to
respectively decrease or increase the request frequency.
