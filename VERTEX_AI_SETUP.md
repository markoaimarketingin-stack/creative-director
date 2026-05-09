# Vertex AI Setup Guide

## Problem with Previous Setup
The old code used a simple API key (`GOOGLE_API_KEY`) which **does NOT work with Vertex AI**. Vertex AI requires OAuth 2.0 service account authentication.

## Solution: Use Service Account Credentials

Vertex AI now uses the proper Google Cloud authentication via the official `google-cloud-aiplatform` SDK.

### Step 1: Create a Service Account in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (1043834745507)
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. Fill in the name: `creative-director-vertex-ai`
6. Click **Create and Continue**

### Step 2: Grant Required Permissions

When prompted for permissions, grant the following roles:
- **Vertex AI Admin** (for image generation access)
- **Editor** (for full access - simplest option)

Click **Continue** and then **Done**.

### Step 3: Download Service Account Key

1. Click on the newly created service account
2. Go to the **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Click **Create** - this downloads a JSON file

### Step 4: Set Environment Variable

The JSON key file needs to be accessible to the application. There are two ways:

**Option A: Local Development (Recommended)**
```bash
# On Windows PowerShell:
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\service-account-key.json"

# On Linux/Mac:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

**Option B: Render Deployment**
1. In Render dashboard, go to your Creative Director service
2. Go to **Environment**
3. Add variable: `GOOGLE_APPLICATION_CREDENTIALS`
4. For the value, paste the **entire contents** of your service account JSON file
5. Click **Save** - Render will create the file from the content

### Step 5: Remove Unused Variable

You can remove `GOOGLE_API_KEY` from your `.env` file - it's no longer used:
```bash
# REMOVE THIS LINE:
# GOOGLE_API_KEY=your_old_api_key_here
```

### Step 6: Test the Setup

```bash
# Local testing
python -c "from google.cloud import aiplatform; aiplatform.init(project='1043834745507', location='us-central1'); print('✅ Vertex AI authentication working!')"
```

## How It Works Now

1. **Google Cloud SDK** reads credentials from:
   - `GOOGLE_APPLICATION_CREDENTIALS` environment variable (service account JSON file)
   - gcloud CLI credentials
   - Application Default Credentials chain

2. **Authentication Flow**:
   - Application → Google Cloud SDK → OAuth 2.0 tokens
   - No API key needed!

3. **Image Generation**:
   - Vertex AI Imagen 3.0 generates images
   - Images saved locally in `output/vertex_ai_images/`
   - Returned as file paths to frontend

## Troubleshooting

### "Vertex AI... not available" Error
This means `GOOGLE_APPLICATION_CREDENTIALS` is not set or the file doesn't exist.

**Fix:**
```bash
# Check environment variable is set
echo $env:GOOGLE_APPLICATION_CREDENTIALS  # Windows
echo $GOOGLE_APPLICATION_CREDENTIALS      # Linux/Mac

# Verify file exists
Test-Path "C:\path\to\service-account-key.json"
```

### "Permission denied" Error
The service account doesn't have Vertex AI permissions.

**Fix:**
1. Go back to [Google Cloud Console](https://console.cloud.google.com/)
2. Go to **IAM & Admin** → **IAM**
3. Find your service account (creative-director-vertex-ai)
4. Click Edit
5. Add **Vertex AI User** role
6. Click Save

### Still Getting Fallback Providers
Check the Render logs - you should see in logs when image generation is attempted.

If it says `"Status: CreativeStatus.GENERATED"` with `provider: "vertex-ai"`, then Vertex AI is working!

## Configuration (No Changes Needed)

Your `.env` already has the correct setup:
```
VERTEX_AI_PROJECT_ID=1043834745507
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_PROVIDER=imagen
VERTEX_AI_IMAGE_MODEL=imagen-3.0-generate-001
```

Just add the `GOOGLE_APPLICATION_CREDENTIALS` environment variable!

To use Nano Banana on Vertex AI, switch to:
```
VERTEX_AI_PROVIDER=gemini_image
VERTEX_AI_IMAGE_MODEL=gemini-2.5-flash-image
```
