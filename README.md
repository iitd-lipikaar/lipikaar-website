# Steps to run Locally
### Working Directory Setup
Let's assume you're working in the directory `~/websites/lipikar`

### Clone this repository
`git clone https://github.com/AbhilakshSinghReen/lipikar-backend.git`

### Move into the project directory
`cd lipikar_backend`
You should now be in the `~/websites/lipikar/lipikar-backend` directory.

### Create and activate a Virtual Environment
`python3 -m venv env`
Now, you should have a folder called `env` in the `~/websites/lipikar/lipikar-backend` folder.

Activate this virtual environment.
`source env/bin/activate`

### Install the dependencies
It is recommended to use a virtual environment.
`pip install -r requirements.txt`

### Create .env file and configure environment variables
`cp .env.sample .env`
Edit the newly created `.env` file to configure your environment variables.

### Make migrations and migrate
`python3 manage.py makemigrations`
`python3 manage.py migrate --run-syncdb`

Check if the SQLite DB file was created successfully:
`if ! test -f db.sqlite3; then echo "SQLite DB not found."; else echo "SQLite DB found, all good."; fi`
You should get an output saying: "SQLite DB found, all good."

### Create Superuser
`python3 manage.py createsuperuser`

### Collect static files
`python3 manage.py collectstatic`

### Test the server
`sudo ufw allow {{lipikar_port}}`
`python3 manage.py runserver 0.0.0.0:{{lipikar_port}}`

On your local machine, open up a browser and try visiting the following URL
`http://{{your_server_ip}}:{{lipikar_port}}/admin/`
You should see the "Lipikar Administration" login screen.

### Running the Server with a Gunicorn process
Stop the server if it is running.
You should still be in the `~/websites/lipikar/lipikar-backend` directory and the virtual environment should be activated.

Install Gunicorn and try running the project with it
`pip install gunicorn`
`gunicorn ocr_app.wsgi:application --bind 0.0.0.0:{{lipikar_port}}`

Try visiting `http://{{your_server_ip}}:{{lipikar_port}}/admin/` on your local machine, you should see the Lipikar admin login page.

#### Create Gunicorn systemd Service file
`sudo nano /etc/systemd/system/lipikar_gunicorn.service`

Paste the following content into the file:
```
[Unit]
Description=lipikar gunicorn daemon
After=network.target

[Service]
User={{username}}
Group={{username}}
WorkingDirectory=/home/{{username}}/websites/lipikar/lipikar-backend
ExecStart=/home/{{username}}/websites/lipikar/lipikar-backend/env/bin/gunicorn \
          --access-logfile /home/{{username}}/websites/lipikar/lipikar-backend/logs/gunicorn_access.log \
          --error-logfile /home/{{username}}/websites/lipikar/lipikar-backend/logs/gunicorn_error.log \
          --workers 3 \
          --bind 0.0.0.0:{{lipikar_port}} \
          ocr_app.wsgi:application
Restart=always
[Install]
WantedBy=multi-user.target
```

Start the Gunicorn service and enable it.
`sudo systemctl start lipikar_gunicorn.service`
`sudo systemctl enable lipikar_gunicorn.service`
`sudo systemctl status lipikar_gunicorn.service`
You should get "active (running)" displayed in green.

You should still be able to visit `http://{{your_server_ip}}:{{lipikar_port}}/admin/` and see the Lipikar Admin page.

### Set up Nginx and Reverse Proxy
`sudo apt install nginx`
`sudo nano /etc/nginx/sites-available/lipikar`

Paste the following content into the file:
```
server {
    listen 80;
    server_name {{your_server_up}};

    location /static/ {
        root /home/lipikar/websites/lipikar/lipikar-backend;
    }
    location /media/ {
        root /home/lipikar/websites/lipikar/lipikar-backend;
    }

    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:{{lipikar_port}};
    }
}
```

Create a symlink from `sites-available` to `sites-enabled`
`sudo ln -s /etc/nginx/sites-available/lipikar /etc/nginx/sites-enabled`

Test the Nginx configuration
`sudo nginx -t`
Test should show that it was successful.

Restart Nginx
`sudo systemctl restart nginx`

Allow Nginx through the firewall.
`sudo ufw allow 'Nginx Full'`

Remove the rule we added earlier to allow port {{lipikar_port}}.
` sudo ufw delete allow {{lipikar_port}}`

### Test Lipikar
Visit `http://{{your_server_up}}` in your web browser. You should see a Lipikar page.

Reboot the server and wait for it to start back up.
`sudo reboot`

Now try visiting `http://{{your_server_up}}` again to check if everything works as expected.

---

### Set up Redis and Celery
#### Prerequisites
1) Before setting up and testing Celery, you should have the Lipikar Document Parsers and OCR APIs set up and running. Make sure to add their provider URLs to the `.env` file and then restart `gunicorn` and `nginx`.
2) To test the OCR functionality, you will need to have a user that has login as well as compute permissions.

#### Install Redis
`sudo apt install redis-server`

Test if redis is running using the command: `redis-cli ping`.
You should get "PONG" in the response.

#### Test Celery
Activate the virtual environment and move into the project directory.
`cd ~/websites/lipikar/lipikar-backend`
`source env/bin/activate`

Run the Celery process
`celery -A ocr.celery worker -Q re_run_ocr,ocr_for_service,new_uploads -Ofair --pool=solo -l INFO`

After a few seconds, you should see a message indicating that Celery is ready.

Now, go to your browser and try uploading a new file for OCR.
The Celery terminal should show that it received and processed one task.

#### Celery systemd service
Similar to how we set up the Gunicorn systemd service, we will set up one for Celery.

`sudo nano /etc/systemd/system/celery.service`

Paste the following content into the file
```
[Unit]
Description=celery daemon
Requires=redis.service
After=network.target redis.service

[Service]
User={{username}}
Group={{username}}
WorkingDirectory=/home/{{username}}/websites/lipikar/lipikar-backend
ExecStart=/home/{{username}}/websites/lipikar/lipikar-backend/env/bin/celery \
          celery -A ocr.celery worker \
          -Q re_run_ocr,ocr_for_service,new_uploads \
          -Ofair \
          --pool=solo \
          -l INFO \
          -f /home/{{username}}/websites/lipikar/celery.log
Restart=always
[Install]
WantedBy=multi-user.target
```

`sudo systemctl start celery`
`sudo systemctl enable celery`
`sudo systemctl status celery`

#### Updating the Gunicorn systemd service
We would like to change the Gunicorn systemd service so that it starts after the redis and celery services.

Here is the complete updated file.
```
[Unit]
Description=gunicorn daemon
Requires=redis.service celery.service
After=network.target redis.service celery.service

[Service]
User={{username}}
Group={{username}}
WorkingDirectory=/home/{{username}}/websites/lipikar/lipikar-backend
ExecStart=/home/{{username}}/websites/lipikar/lipikar-backend/env/bin/gunicorn \
          --access-logfile /home/{{username}}/websites/lipikar/gunicorn_access.log \
          --error-logfile /home/{{username}}/websites/lipikar/gunicorn_error.log \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          ocr_app.wsgi:application
Restart=always
[Install]
WantedBy=multi-user.target
```

`sudo systemctl daemon-reload`

Restart and check the redis service
`sudo systemctl restart redis`
`sudo systemctl status redis`
You should see "active (running)" in green.

Restart and check the celery service
`sudo systemctl restart celery`
`sudo systemctl status celery`
You should see "active (running)" in green.

Restart and check the gunicorn service
`sudo systemctl restart gunicorn`
`sudo systemctl status gunicorn`
You should see "active (running)" in green.

### Test Lipikar (Again)
Visit `http://{{your_server_up}}` in your web browser. Try uploading a new file and check the results.

Reboot the server and wait for it to start back up.
`sudo reboot`

Now try visiting `http://{{your_server_up}}` again to check if everything works as expected.
