# Open-VPN-WebPanel-for-Antizapret
Простенька админ панель для бота в ТГ https://github.com/VATAKATru61/TG-Bot-OpenVPN-Antizapret/
Установка только вручную
Пройдитесь по всем файлам и замените на ВСТАВЬ СВОЕ на свое)
  
  По возможности буду добавлять  
  Что умеет:
  - :white_check_mark: Информация о сервере. С кнопкой обновления  
  - :white_check_mark: 2 темы. Белая и темная, белая по умолччанию
  - :white_check_mark: Добавление пользователей
  - :white_check_mark: Скачивание готовых конфигов OpenVPN(обычный и Antizapret)
  - :white_check_mark: Установка срока действия ключа
  - :white_check_mark: Удаление пользователей
  - :white_check_mark: Показ Пользователей онлайн


  В планах:
- Полный функционал как в боте так и тут (если появится время)

Подготовка и запуск
- Файлы кинуть в ```/roor/ваша_папка```
- Перейти в эту папку и создать виртуальное окружение
```
cd /root/ваша_папка
python3 -m venv venv
```
- Активировать его и установи зависимости(может не полный список, в консоле при запуске выдаст ошибку, поймете какие нужны и доустановите)
```
source /root/ваша_папка/venv/bin/activate
pip install fastapi uvicorn jinja2 psutil python-multipart
```
Запустить 
```
uvicorn webpanel:app --host 0.0.0.0 --port 7000
```

Если всё оё то будет 
```
Jun 01 20:30:24 vpn uvicorn[337297]: INFO:     Started server process [337297]
Jun 01 20:30:24 vpn uvicorn[337297]: INFO:     Waiting for application startup.
Jun 01 20:30:24 vpn uvicorn[337297]: INFO:     Application startup complete.
Jun 01 20:30:24 vpn uvicorn[337297]: INFO:     Uvicorn running on http://0.0.0.0:7000 (Press CTRL+C to quit)
```
Панель будет доступна по адресу http://IP:7000 (Порт можно сменить, просто при запуске unicorn введите другой)
Проще будет запуск через ```systemd```
```
sudo nano /etc/systemd/system/webpanel.service
```
Вставляете, но впишите свой путь
```
[Unit]
Description=Uvicorn for webpanel (FastAPI) service
After=network.target

[Service]
WorkingDirectory=/root/ваша папка
# Пути виртуального окружения + стандартные системные папки
Environment="PATH=/root/1/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/1/venv/bin/uvicorn webpanel:app --host 0.0.0.0 --port 7000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Перезагрузите конфигурацию systemd, чтобы он подхватил новый юнит
```
sudo systemctl daemon-reload
```
Запустите сервис вручную и убедитесь, что всё работает
```
sudo systemctl start webpanel.service
sudo systemctl status webpanel.service
```
Включите автозапуск при загрузке
```
sudo systemctl enable webpanel.service
```
Ну и полезные команды
- Логи
```
sudo journalctl -u webpanel.service -f
```
- Остановить/Перезапустить
```
sudo systemctl stop webpanel.service
sudo systemctl restart webpanel.service
```
- Отключить автозапуск
```
sudo systemctl disable webpanel.service
```



Скриншот ![Иллюстрация к проекту](https://github.com/VATAKATru61/Open-VPN-WebPanel-for-Antizapret/blob/main/index.jpg)
