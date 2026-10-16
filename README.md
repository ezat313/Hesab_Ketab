# حساب و کتاب خانه

سایت ساده برای ثبت مصارف خانه به صورت مشترک بین اعضای یک خانواده، با تقویم شمسی و پول افغانی.

## اجرا روی کمپیوتر خودتان

```powershell
cd C:\Users\Ezatullah\Desktop\hesab_ketab
python -m venv .venv                         # فقط یک بار
.venv\Scripts\pip install -r requirements.txt  # فقط یک بار
.venv\Scripts\python app.py
```

بعد در مرورگر باز کنید: http://127.0.0.1:8000

## آپلود روی PythonAnywhere (حساب رایگان)

در دستورهای زیر به جای `USERNAME` نام کاربری PythonAnywhere خود را بنویسید.

1. در [pythonanywhere.com](https://www.pythonanywhere.com) یک حساب رایگان (Beginner) بسازید.
2. پوشهٔ پروژه را **بدون** `.venv` و `instance` زیپ کنید و در تب **Files** آپلود کنید.
3. در تب **Consoles** یک **Bash** باز کنید و این دستورها را بزنید:
   ```bash
   unzip hesab_ketab.zip -d ~/hesab_ketab
   mkvirtualenv --python=python3.13 hesab-venv
   pip install -r ~/hesab_ketab/requirements.txt
   ```
   اگر `python3.13` نبود، جدیدترین نسخه‌ای را که موجود است انتخاب کنید (3.10 یا بالاتر).
4. در تب **Web** گزینهٔ **Add a new web app** را بزنید، **Manual configuration** و همان نسخهٔ Python را انتخاب کنید.
5. در همان صفحه این‌ها را تنظیم کنید:
   - **Source code:** `/home/USERNAME/hesab_ketab`
   - **Virtualenv:** `/home/USERNAME/.virtualenvs/hesab-venv`
   - **Static files:** URL را `/static/` و Directory را `/home/USERNAME/hesab_ketab/static` بگذارید
   - **Force HTTPS:** روشن
6. فایل **WSGI configuration** را باز کنید، همه‌چیز داخلش را پاک کنید و این را بنویسید:
   ```python
   import os
   import sys

   path = "/home/USERNAME/hesab_ketab"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["COOKIE_SECURE"] = "1"

   from app import app as application
   ```
7. دکمهٔ سبز **Reload** را بزنید. سایت در `https://USERNAME.pythonanywhere.com` باز می‌شود.

### نکته‌ها
- سایت رایگان باید هر چند ماه یک بار از تب **Web** تمدید شود. PythonAnywhere پیش از آن ایمیل می‌فرستد.
- همهٔ معلومات در فایل `instance/hesab.db` است. گاه‌گاهی از تب **Files** آن را دانلود کنید تا پشتیبان داشته باشید.
- بعد از هر تغییر در کد، فایل‌های جدید را آپلود کنید و **Reload** را بزنید.
