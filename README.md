# Tasks

## Настройка и запуск

Перед запуском нужно создать файл `.env` с содержимым из файла `env.sample`
с указанием своих параметров.

Запуск через docker compose.




```shell
docker exec -t -i tasks-backend-1 sh
```

```shell
cat /usr/local/lib/python3.12/site-packages/ckeditor_uploader/urls.py
```

```shell
cat > /usr/local/lib/python3.12/site-packages/ckeditor_uploader/urls.py <<EOF
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.decorators.cache import never_cache

from . import views


urlpatterns = [
    re_path(r"^upload/", login_required(views.upload), name="ckeditor_upload"),
    re_path(
        r"^browse/",
        never_cache(login_required(views.browse)),
        name="ckeditor_browse",
    ),
]
EOF
```
