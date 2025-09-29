# 🌐 RPA Webhook Integration

This document shows how the CTA system sends extracted incident details to your RPA webhook for claim filing.

## Webhook Payload Format

When the CTA system extracts incident details, it sends a POST request to your `RPA_WEBHOOK` URL with the following payload:

```json
{
  "thread_id": "thread_123456789",
  "timestamp": "2024-01-22T13:15:09.123456",
  "source": "burdy_chatbot_cta",
  "incident_details": {
    "date_of_incident": "03/15/2024",
    "month_name": "March",
    "day": 15,
    "year": 2024,
    "zip_code": "90210",
    "was_accident_my_fault": "no",
    "was_issued_ticket": "no",
    "physically_injured": "yes",
    "ambulance_called": "yes",
    "went_to_emergency_room": "yes",
    "injury_types": ["Whiplash", "Broken bones"],
    "attorney_helping": "no",
    "attorney_rejected": null,
    "significant_property_damage": "high",
    "state_of_injury": "California",
    "city_of_injury": "Los Angeles",
    "other_party_vehicle_type": "personal",
    "injury_description": "Neck pain and broken ribs from car accident",
    "first_name": "John",
    "last_name": "Smith",
    "phone_number": "555-123-4567",
    "email": "john.smith@email.com",
    "consent_given": "yes"
  }
}
```

## Webhook Headers

The request includes these headers:
- `Content-Type: application/json`
- Standard HTTP headers

## Response Handling

Your RPA webhook should:
1. **Accept the payload** and validate the data
2. **Process the claim** using the extracted information
3. **Return HTTP 200** for successful processing
4. **Return HTTP 4xx/5xx** for errors

## Example Webhook Handler (Node.js)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhook/claim-filing', (req, res) => {
  try {
    const { thread_id, timestamp, source, incident_details } = req.body;
    
    // Validate required fields
    if (!incident_details || !incident_details.first_name) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    // Process the claim
    const claimData = {
      clientName: `${incident_details.first_name} ${incident_details.last_name}`,
      clientPhone: incident_details.phone_number,
      clientEmail: incident_details.email,
      incidentDate: incident_details.date_of_incident,
      monthName: incident_details.month_name,
      zipCode: incident_details.zip_code,
      location: `${incident_details.city_of_injury}, ${incident_details.state_of_injury}`,
      injuries: incident_details.injury_types,
      ambulanceCalled: incident_details.ambulance_called,
      emergencyRoom: incident_details.went_to_emergency_room,
      propertyDamage: incident_details.significant_property_damage,
      atFault: incident_details.was_accident_my_fault,
      ticketIssued: incident_details.was_issued_ticket,
      attorneyInvolved: incident_details.attorney_helping,
      otherPartyVehicle: incident_details.other_party_vehicle_type,
      consentGiven: incident_details.consent_given
    };
    
    // Your claim filing logic here
    console.log('Processing claim for:', claimData.clientName);
    
    // Simulate claim filing
    const claimId = `CLAIM-${Date.now()}`;
    
    res.status(200).json({
      success: true,
      claimId: claimId,
      message: 'Claim filed successfully',
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(3000, () => {
  console.log('RPA webhook server running on port 3000');
});
```

## Example Webhook Handler (Python/Flask)

```python
from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/webhook/claim-filing', methods=['POST'])
def handle_claim_webhook():
    try:
        data = request.json
        
        # Extract incident details
        incident_details = data.get('incident_details', {})
        thread_id = data.get('thread_id')
        
        # Validate required fields
        if not incident_details.get('first_name'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Process the claim
        claim_data = {
            'client_name': f"{incident_details.get('first_name')} {incident_details.get('last_name')}",
            'client_phone': incident_details.get('phone_number'),
            'client_email': incident_details.get('email'),
            'incident_date': incident_details.get('date_of_incident'),
            'month_name': incident_details.get('month_name'),
            'zip_code': incident_details.get('zip_code'),
            'location': f"{incident_details.get('city_of_injury')}, {incident_details.get('state_of_injury')}",
            'injuries': incident_details.get('injury_types', []),
            'ambulance_called': incident_details.get('ambulance_called'),
            'emergency_room': incident_details.get('went_to_emergency_room'),
            'property_damage': incident_details.get('significant_property_damage'),
            'at_fault': incident_details.get('was_accident_my_fault'),
            'ticket_issued': incident_details.get('was_issued_ticket'),
            'attorney_involved': incident_details.get('attorney_helping'),
            'other_party_vehicle': incident_details.get('other_party_vehicle_type'),
            'consent_given': incident_details.get('consent_given', 'no')
        }
        
        # Your claim filing logic here
        print(f"Processing claim for: {claim_data['client_name']}")
        
        # Simulate claim filing
        claim_id = f"CLAIM-{int(datetime.now().timestamp())}"
        
        return jsonify({
            'success': True,
            'claim_id': claim_id,
            'message': 'Claim filed successfully',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(port=3000, debug=True)
```

## Environment Variables

Make sure to set these environment variables in your chatbot:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_main_assistant_id_here
VALIDATOR_ASSISTANT=your_validator_assistant_id_here

# RPA Integration
RPA_WEBHOOK=https://your-rpa-bot.com/webhook/claim-filing

# Database Configuration
MYSQL_HOST=your_mysql_host
MYSQL_DATABASE=your_database_name
MYSQL_USER=your_database_user
MYSQL_PASSWORD=your_database_password
```

## Testing the Webhook

You can test the webhook integration by:

1. **Starting a conversation** with the chatbot
2. **Providing incident details** in the conversation
3. **Triggering goodbye** to activate CTA
4. **Checking your webhook logs** for the incoming data

## Benefits

- **Automated Claim Filing**: No manual data entry required
- **GPT-Powered Extraction**: High accuracy in data extraction
- **Real-time Processing**: Immediate webhook notification
- **Structured Data**: Clean, organized data for your RPA bot
- **Error Handling**: Robust error handling and logging

This integration allows your RPA bot to automatically file claims based on the conversation data extracted by the GPT assistant, streamlining your legal intake process.

