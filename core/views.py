# core/views.py
import os
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.rest import Client
from core.models import User, Transaction

@csrf_exempt
def ussd_callback(request):
    """
    Handles StarSave USSD (*123#) for Amina to join, save $1, withdraw $10, check balance.
    - Expects Africa’s Talking POST: sessionId, phoneNumber, text (e.g., "1*1234").
    - Returns CON (menu) or END (final response).
    - Test mode: Mocks M-Pesa deposit, cKES withdrawal, month 6 balance ($6).
    - SMS via Twilio for feedback (e.g., "Balance: $1").
    - Stores User (phone, PIN, balance), Transaction (mock tx).
    """
    if request.method != "POST":
        return HttpResponse("Invalid request", status=400)

    # Extract Africa’s Talking payload
    session_id = request.POST.get("sessionId", "")
    phone_number = request.POST.get("phoneNumber", "")
    text = request.POST.get("text", "")

    # Split user input (e.g., "1*1234" → ["1", "1234"])
    text_array = text.split("*")
    user_response = text_array[-1] if text_array else ""

    # Initialize Twilio client
    twilio_client = Client(
        os.environ.get("TWILIO_ACCOUNT_SID"),
        os.environ.get("TWILIO_AUTH_TOKEN")
    )
    twilio_number = os.environ.get("TWILIO_PHONE_NUMBER")

    # USSD Logic
    if text == "":
        # Initial *123#: Main menu
        response = "CON Welcome to ZidiSave\n1. Join\n2. Save $1\n3. Withdraw $10\n4. Check Balance"
    elif text_array[0] == "1":
        # Join flow
        if len(text_array) == 1:
            response = "CON Enter 4-digit PIN"
        elif len(text_array) == 2 and len(user_response) == 4:
            # Save user with mock Celo address
            try:
                user, created = User.objects.get_or_create(
                    phone=phone_number,
                    defaults={
                        "pin": user_response,
                        "celo_address": f"0xmock{phone_number[-6:]}",
                        "balance": 0.00
                    }
                )
                if not created and user.pin != user_response:
                    response = "END Invalid PIN"
                else:
                    # Send welcome SMS
                    twilio_client.messages.create(
                        body="Welcome to ZidiSave! Save for your family.",
                        from_=twilio_number,
                        to=phone_number
                    )
                    response = "END Joined ZidiSave successfully"
            except Exception as e:
                response = "END Error joining: Try again"
        else:
            response = "END Invalid PIN: Enter 4 digits"
    elif text_array[0] == "2":
        # Save $1 flow
        try:
            user = User.objects.get(phone=phone_number)
            if len(text_array) == 1:
                response = "CON Pay $1 (KSH 130) to save?"
            elif user_response == "1":
                # Mock M-Pesa deposit (no blockchain yet, Step 3)
                user.balance += 1.00
                user.save()
                Transaction.objects.create(
                    user=user,
                    tx_hash=f"0xmock_save_{session_id}",
                    amount=1.00,
                    type="deposit"
                )
                # Send SMS
                twilio_client.messages.create(
                    body=f"MamaJamii Fund: $1 saved! Balance: ${user.balance}",
                    from_=twilio_number,
                    to=phone_number
                )
                response = "END Saved $1 successfully"
            else:
                response = "END Invalid input"
        except User.DoesNotExist:
            response = "END Join ZidiSave first"
    elif text_array[0] == "3":
        # Withdraw $10 flow
        try:
            user = User.objects.get(phone=phone_number)
            if len(text_array) == 1:
                response = "CON Enter PIN to withdraw $10"
            elif len(text_array) == 2:
                if user.pin == user_response and user.balance >= 10.00:
                    # Mock withdrawal (no blockchain yet)
                    fee = 0.20
                    amount = 10.00
                    user.balance -= amount
                    user.save()
                    Transaction.objects.create(
                        user=user,
                        tx_hash=f"0xmock_withdraw_{session_id}",
                        amount=amount,
                        type="withdraw"
                    )
                    # Send SMS
                    twilio_client.messages.create(
                        body=f"Withdrew $9.80 cKES for family! Fee: ${fee}",
                        from_=twilio_number,
                        to=phone_number
                    )
                    response = "END Withdrew $10 successfully"
                else:
                    response = "END Invalid PIN or insufficient balance"
            else:
                response = "END Invalid input"
        except User.DoesNotExist:
            response = "END Join ZidiSave first"
    elif text_array[0] == "4":
        # Check balance
        try:
            user = User.objects.get(phone=phone_number)
            # Mock month 6 for demo: Hardcode $6 if balance >= 1
            display_balance = 6.00 if user.balance >= 1 else user.balance
            response = f"END MamaJamii Fund: ${display_balance}"
            # Send SMS
            twilio_client.messages.create(
                body=f"MamaJamii Fund: ${display_balance} saved!",
                from_=twilio_number,
                to=phone_number
            )
        except User.DoesNotExist:
            response = "END Join ZidiSave first"
    else:
        response = "END Invalid option"

    return HttpResponse(response, content_type="text/plain")