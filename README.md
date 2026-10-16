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

در دستورهای زیر به جای `USERNAME` نام کاربری PythonAnywhere و به جای `GITHUB_USER` نام کاربری GitHub خود را بنویسید.

1. در [pythonanywhere.com](https://www.pythonanywhere.com) یک حساب رایگان (Beginner) بسازید.
2. در تب **Consoles** یک **Bash** باز کنید و کد را از GitHub بگیرید و کتابخانه‌ها را نصب کنید:
   ```bash
   git clone https://github.com/GITHUB_USER/hesab_ketab.git ~/hesab_ketab
   mkvirtualenv --python=python3.13 hesab-venv
   pip install -r ~/hesab_ketab/requirements.txt
   ```
   اگر `python3.13` نبود، جدیدترین نسخه‌ای را که موجود است انتخاب کنید (3.10 یا بالاتر).
3. در تب **Web** گزینهٔ **Add a new web app** را بزنید، **Manual configuration** و همان نسخهٔ Python را انتخاب کنید.
4. در همان صفحه این‌ها را تنظیم کنید:
   - **Source code:** `/home/USERNAME/hesab_ketab`
   - **Virtualenv:** `/home/USERNAME/.virtualenvs/hesab-venv`
   - **Static files:** URL را `/static/` و Directory را `/home/USERNAME/hesab_ketab/static` بگذارید
   - **Force HTTPS:** روشن
5. فایل **WSGI configuration** را باز کنید، همه‌چیز داخلش را پاک کنید و این را بنویسید:
   ```python
   import os
   import sys

   path = "/home/USERNAME/hesab_ketab"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ["COOKIE_SECURE"] = "1"

   from app import app as application
   ```
6. دکمهٔ سبز **Reload** را بزنید. سایت در `https://USERNAME.pythonanywhere.com` باز می‌شود.

### نکته‌ها
- سایت رایگان باید هر چند ماه یک بار از تب **Web** تمدید شود. PythonAnywhere پیش از آن ایمیل می‌فرستد.
- همهٔ معلومات در فایل `instance/hesab.db` است. گاه‌گاهی از تب **Files** آن را دانلود کنید تا پشتیبان داشته باشید.
- **به‌روزرسانی سایت بعد از هر تغییر:** تغییرات را از کمپیوتر به GitHub بفرستید (`git push`)، بعد در Bash کنسول PythonAnywhere این را بزنید و در تب **Web** دکمهٔ **Reload** را فشار دهید:
  ```bash
  cd ~/hesab_ketab && git pull
  ```
  اگر `requirements.txt` تغییر کرده بود، قبل از Reload این را هم بزنید: `workon hesab-venv && pip install -r requirements.txt`
