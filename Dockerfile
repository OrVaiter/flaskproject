FROM python:3.11-slim

# הגדרת תיקייה פנימית באפליקציה
WORKDIR /app

# התקנת תלויות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת כל שאר הקבצים
COPY . .

# פתיחת פורט Flask
EXPOSE 5000

# הפעלת האפליקציה
CMD ["python", "app.py"]
