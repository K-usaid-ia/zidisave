# core/views.py
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def ussd_callback(request):
    """
    Handles USSD requests from Africa’s Talking for StarSave (*123#).
    - Expects POST with sessionId, phoneNumber, text (user input).
    - Returns CON (menu) or END (final response).
    - Stub: Returns "Welcome to ZidiSave" for initial *123#.
    - Later: Expands to join, save $1, withdraw $10 (Steps 2, 4–5).
    """
    if request.method == "POST":
        session_id = request.POST.get("sessionId", "")
        phone_number = request.POST.get("phoneNumber", "")
        text = request.POST.get("text", "")

        if text == "":
            # Initial *123#: Show welcome menu
            response = "CON Welcome to ZidiSave\n1. Join\n2. Save\n3. Withdraw"
        else:
            # Placeholder for later menus (Step 2)
            response = "END Not implemented yet"

        return HttpResponse(response, content_type="text/plain")

    return HttpResponse("Invalid request", status=400)