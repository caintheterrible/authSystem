### Server design studies, research and remarks

May 24, 2024.

Set up basic directory structure for django application.
Thinking about how to progress from here, I think I will start with simpler
configurations first, like logging functionality and database design.

1. For design, Django will be made to expect two configurations: `base.py` and `database.py` files.
   * `base.py` will hold all base configurations necessary for Django deployment. This will serve `BaseConfiguration` class to be extended by environment-specific deploys like `development.py` or `production.py` files.
   * `database.py` will serve database configurations, preferably PostgreSQL but for speed and development purposes will rely on SQLite for now.
2. These configurations will be served to `deploy.py` to centralize all preferences and minimalize 'cannot be found' errors. `deploy.py` will serve as `DJANGO_SETTINGS_MODULE` for `manage.py` run point.

These are to establish grounds for efficient code management through modular design.