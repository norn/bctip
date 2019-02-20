# BCH Tip - Printable Bitcoin Cash (BCH) Tips

Python/Django project, runs on [tips.bitcoin.com](https://tips.bitcoin.com/)

## Development

1. Create virtual env
2. Copy `bctip/local_settings.py.example`, `bctip/settings.py.example`, and `bctip/wsgi.py.example` to drop the `.example` ending and edit for local settings
3. Start Bitcoin ABC full node
4. Activate python virtual environment
```
$ virtualenv env
$ source env/bin/activate
```
5. With virtual environment activated:

Collect necessary static files for the app
```
(env) $ python manage.py collectstatic
```

Initialize database
```
(env) $ python manage.py makemigrations
(env) $ python manage.py migrate
```

6. Run the app in local browser
```
(env) $ python manage.py runserver
```

7. Open browser and navigate to `localhost:8000`
8. Test `return_expired.py` by running the script manually
```
(env) $ python utils/return_expired.py
```

## Production

Starting with a fresh Ubuntu 16.04 server...

1. Install git and nginx

```
sudo apt install git
sudo apt-get install nginx
```

2. Clone this git repository into `/var/www/bch-tip`
3. Copy `bctip/local_settings.py.example`, `bctip/settings.py.example`, and `bctip/wsgi.py.example` to drop the `.example` ending and edit for local settings
4. `cd` into the repo directory, e.g. `cd /var/www/bch-tip`
6. Install and activate python virtual environment, then install requirements and configure database
```
$ sudo apt-install virtualenv
$ virtualenv env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
(env) $ python manage.py makemigrations
(env) $ python manage.py migrate
(env) $ python manage.py collectstatic
(env) $ deactivate
$ 
```
7. Create `systemctl` service for deployment with `gunicorn`
8. Configure `nginx` for appropriate URL, matching other settings config files
9. Deploy with `systemctl`
10. Set up crontab to run `/utils/return_expired.py`

The script will output a log to `return_expired.log` in root directory of the git repo