# core/views.py
import os
import re
from decimal import Decimal
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.rest import Client
from core.models import User, Transaction
import logging

logger = logging.getLogger('django')

@csrf_exempt
def ussd_callback(request):
    """
    Handles StarSave USSD (*123#) for Amina to join, save $1, withdraw $10, check balance.
    - Expects Africa’s Talking POST: sessionId, phoneNumber, text (e.g., "1*1234").
    - Returns CON (menu) or END (final response).
    - Test mode: Mocks M-Pesa deposit, cKES withdrawal, month 6 balance ($6).
    - SMS via Twilio, skips if unavailable.
    - Fixes: Decimal for balance, robust Twilio handling.
    """
    try:
        if request.method != "POST":
            logger.error("Invalid method: %s", request.method)
            return HttpResponse("Invalid request", status=400)

        # Extract payload
        session_id = request.POST.get("sessionId", "")
        phone_number = request.POST.get("phoneNumber", "")
        text = request.POST.get("text", "")

        # Validate phone_number
        # if not re.match(r"^\+\d{10,15}$", phone_number):
        #     logger.error("Invalid phone_number: %s", phone_number)
        #     return HttpResponse("END Invalid phone number", status=200)

        # Split input
        text_array = text.split("*")
        user_response = text_array[-1] if text_array else ""

        # Initialize Twilio (optional)
        twilio_client = None
        twilio_number = None
        if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"):
            try:
                twilio_client = Client(
                    os.environ.get("TWILIO_ACCOUNT_SID"),
                    os.environ.get("TWILIO_AUTH_TOKEN")
                )
                twilio_number = os.environ.get("TWILIO_PHONE_NUMBER")
                if not twilio_number or twilio_number == phone_number:
                    logger.error("Invalid Twilio number: %s", twilio_number)
                    twilio_client = None  # Skip SMS if invalid
            except Exception as e:
                logger.error("Twilio init failed: %s", str(e))

        # USSD Logic
        if text == "":
            response = "CON Welcome to ZidiSave\n1. Join\n2. Save $1\n3. Withdraw $10\n4. Check Balance"
        elif text_array[0] == "1":
            # Join
            if len(text_array) == 1:
                response = "CON Enter 4-digit PIN"
            elif len(text_array) == 2:
                if len(user_response) != 4 or not user_response.isdigit():
                    response = "END PIN must be 4 digits"
                else:
                    try:
                        user, created = User.objects.get_or_create(
                            phone=phone_number,
                            defaults={
                                "pin": user_response,
                                "celo_address": f"0xmock{phone_number[-6:]}",
                                "balance": Decimal('0.00')
                            }
                        )
                        if not created and user.pin != user_response:
                            response = "END User exists with different PIN"
                        else:
                            if twilio_client and twilio_number:
                                try:
                                    twilio_client.messages.create(
                                        body="Welcome to ZidiSave! Save for your family.",
                                        from_=twilio_number,
                                        to=phone_number
                                    )
                                except Exception as e:
                                    logger.error("Join SMS failed: %s", str(e))
                            response = "END Joined ZidiSave successfully"
                    except Exception as e:
                        logger.error("Join error: %s", str(e))
                        response = "END Error joining: Contact support"
            else:
                response = "END Invalid input"
        elif text_array[0] == "2":
            # Save $1
            try:
                user = User.objects.get(phone=phone_number)
                if len(text_array) == 1:
                    response = "CON Pay $1 (KSH 130) to save?"
                elif user_response == "1":
                    user.balance += Decimal('1.00')
                    user.save()
                    Transaction.objects.create(
                        user=user,
                        tx_hash=f"0xmock_save_{session_id}",
                        amount=Decimal('1.00'),
                        type="deposit"
                    )
                    if twilio_client and twilio_number:
                        try:
                            twilio_client.messages.create(
                                body=f"MamaJamii Fund: $1 saved! Balance: ${user.balance}",
                                from_=twilio_number,
                                to=phone_number
                            )
                        except Exception as e:
                            logger.error("Save SMS failed: %s", str(e))
                    response = "END Saved $1 successfully"
                else:
                    response = "END Invalid input"
            except User.DoesNotExist:
                response = "END Join ZidiSave first"
        elif text_array[0] == "3":
            # Withdraw $10
            try:
                user = User.objects.get(phone=phone_number)
                if len(text_array) == 1:
                    response = "CON Enter PIN to withdraw $10"
                elif len(text_array) == 2:
                    if user.pin == user_response and user.balance >= Decimal('10.00'):
                        fee = Decimal('0.20')
                        amount = Decimal('10.00')
                        user.balance -= amount
                        user.save()
                        Transaction.objects.create(
                            user=user,
                            tx_hash=f"0xmock_withdraw_{session_id}",
                            amount=amount,
                            type="withdraw"
                        )
                        if twilio_client and twilio_number:
                            try:
                                twilio_client.messages.create(
                                    body=f"Withdrew $9.80 cKES for family! Fee: ${fee}",
                                    from_=twilio_number,
                                    to=phone_number
                                )
                            except Exception as e:
                                logger.error("Withdraw SMS failed: %s", str(e))
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
                display_balance = Decimal('6.00') if user.balance >= Decimal('1.00') else user.balance
                response = f"END MamaJamii Fund: ${display_balance}"
                if twilio_client and twilio_number:
                    try:
                        twilio_client.messages.create(
                            body=f"MamaJamii Fund: ${display_balance} saved!",
                            from_=twilio_number,
                            to=phone_number
                        )
                    except Exception as e:
                        logger.error("Balance SMS failed: %s", str(e))
            except User.DoesNotExist:
                response = "END Join ZidiSave first"
        else:
            response = "END Invalid option"

        return HttpResponse(response, content_type="text/plain")

    except Exception as e:
        logger.error("USSD critical error: %s", str(e))
        return HttpResponse("END Server error, try again", status=500)