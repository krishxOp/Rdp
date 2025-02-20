from flask import Flask, request, render_template_string, redirect, url_for, flash
from instagrapi import Client
import os
import time
import re
import textwrap  # For splitting long messages

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_secret_key")

# Initialize Instagram Client (Persistent Login)
cl = Client()

# Instagram DM character limit (estimate)
INSTAGRAM_MESSAGE_LIMIT = 1000  # Adjust if needed

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Message Sender</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: black; color: red; text-align: center; }
        .container { background-color: white; padding: 20px; border-radius: 10px; width: 350px; margin: auto; }
        h1 { color: red; }
        input, select, button { width: 100%; padding: 10px; margin-top: 10px; }
        button { background-color: black; color: red; font-weight: bold; cursor: pointer; }
        button:hover { background-color: red; color: white; }
        .message { font-size: 14px; color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Instagram Message Sender</h1>
        <form action="/" method="POST" enctype="multipart/form-data">
            <input type="text" name="username" placeholder="Instagram Username" required>
            <input type="password" name="password" placeholder="Instagram Password" required>
            <select name="choice" required>
                <option value="inbox">Inbox</option>
                <option value="group">Group</option>
            </select>
            <input type="text" name="target_username" placeholder="Target Username (Inbox only)">
            <input type="text" name="chat_link" placeholder="Group Chat Link (Group only)">
            <input type="file" name="message_file" required>
            <input type="number" name="delay" placeholder="Delay (milliseconds)" required>
            <button type="submit">Send Messages</button>
        </form>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="message">
                    {% for category, message in messages %}
                        <p class="{{ category }}">{{ message }}</p>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
    </div>
</body>
</html>
'''

# Function to extract thread ID from chat link
def extract_thread_id(url):
    match = re.search(r"instagram\.com/direct/t/(\d+)", url)
    return match.group(1) if match else None

# Function to split long messages into chunks
def split_message(message, limit=INSTAGRAM_MESSAGE_LIMIT):
    return textwrap.wrap(message, width=limit, break_long_words=False, replace_whitespace=False)

@app.route("/", methods=["GET", "POST"])
def send_instagram_messages():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        choice = request.form.get("choice")
        target_username = request.form.get("target_username")
        chat_link = request.form.get("chat_link")
        delay_ms = request.form.get("delay")

        # Validate input
        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for("send_instagram_messages"))

        if choice == "inbox" and not target_username:
            flash("Target username is required for inbox messaging.", "error")
            return redirect(url_for("send_instagram_messages"))

        if choice == "group":
            if not chat_link:
                flash("Group chat link is required for group messaging.", "error")
                return redirect(url_for("send_instagram_messages"))
            thread_id = extract_thread_id(chat_link)
            if not thread_id:
                flash("Invalid Instagram group chat link. Please enter a valid URL.", "error")
                return redirect(url_for("send_instagram_messages"))
        else:
            thread_id = None  # Not needed for inbox messages

        if not delay_ms.isdigit() or int(delay_ms) < 0:
            flash("Delay must be a non-negative number.", "error")
            return redirect(url_for("send_instagram_messages"))

        delay_ms = int(delay_ms)

        # Validate message file
        message_file = request.files.get("message_file")
        if not message_file:
            flash("Message file is required!", "error")
            return redirect(url_for("send_instagram_messages"))

        messages = message_file.read().decode("utf-8").splitlines()
        if not messages:
            flash("Message file is empty!", "error")
            return redirect(url_for("send_instagram_messages"))

        # Login to Instagram (Only if not already logged in)
        try:
            if not cl.user_id:
                cl.login(username, password)
                flash("Login successful!", "success")
        except Exception as e:
            flash(f"Login failed: {str(e)}", "error")
            return redirect(url_for("send_instagram_messages"))

        # Send messages (handling long messages)
        try:
            for message in messages:
                message_parts = split_message(message)

                for part in message_parts:
                    if choice == "inbox":
                        user_id = cl.user_id_from_username(target_username)
                        cl.direct_send(part, [user_id])
                    elif choice == "group":
                        cl.direct_send(part, [], thread_id=thread_id)

                    # Delay in milliseconds
                    time.sleep(delay_ms / 1000)

            flash("All messages sent successfully!", "success")
        except Exception as e:
            flash(f"Error sending messages: {str(e)}", "error")

        return redirect(url_for("send_instagram_messages"))

    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
