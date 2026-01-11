#!/bin/bash

# Google Cloud Run Deployment Script for TradingView Webhook Bot
# This script automates deployment to Google Cloud Run

set -e  # Exit on error

echo "🚀 Starting Google Cloud Run Deployment..."

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="linen-epigram-476218-s9"
SERVICE_NAME="tradingview-webhook"
REGION="us-central1"

echo -e "${BLUE}Step 1: Install Google Cloud SDK${NC}"
echo "Download from: https://cloud.google.com/sdk/docs/install"
echo "Or run: curl https://sdk.cloud.google.com | bash"
echo ""

echo -e "${BLUE}Step 2: Initialize gcloud${NC}"
gcloud init
echo ""

echo -e "${BLUE}Step 3: Authenticate with Google${NC}"
gcloud auth login
echo ""

echo -e "${BLUE}Step 4: Set Project${NC}"
gcloud config set project $PROJECT_ID
echo -e "${GREEN}✓ Project set to: $PROJECT_ID${NC}"
echo ""

echo -e "${BLUE}Step 5: Enable Required APIs${NC}"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

echo -e "${YELLOW}Step 6: Enter your API Keys${NC}"
echo "You will be prompted to enter your API credentials."
echo "These will be set as environment variables during deployment."
echo ""

read -p "Enter BINANCE_API_KEY: " BINANCE_API_KEY
read -sp "Enter BINANCE_API_SECRET: " BINANCE_API_SECRET
echo ""
read -p "Enter FLATTRADE_API_KEY: " FLATTRADE_API_KEY
read -sp "Enter FLATTRADE_API_SECRET: " FLATTRADE_API_SECRET
echo ""
read -p "Enter FLATTRADE_USER_ID: " FLATTRADE_USER_ID
echo ""

echo -e "${BLUE}Step 7: Deploy to Cloud Run${NC}"
echo "Deploying service: $SERVICE_NAME to region: $REGION"
echo ""

gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --memory 512Mi \
  --cpu 1 \
  --allow-unauthenticated \
  --set-env-vars \
    BINANCE_API_KEY=$BINANCE_API_KEY,\
BINANCE_API_SECRET=$BINANCE_API_SECRET,\
BINANCE_TESTNET=true,\
FLATTRADE_API_KEY=$FLATTRADE_API_KEY,\
FLATTRADE_API_SECRET=$FLATTRADE_API_SECRET,\
FLATTRADE_USER_ID=$FLATTRADE_USER_ID

echo ""
echo -e "${GREEN}✓ Deployment completed!${NC}"
echo ""
echo -e "${BLUE}Step 8: Get Webhook URL${NC}"
WEBHOOK_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo -e "${GREEN}Your webhook URL:${NC}"
echo -e "${YELLOW}$WEBHOOK_URL${NC}"
echo ""

echo -e "${BLUE}Step 9: Test Health Endpoint${NC}"
echo "Testing: $WEBHOOK_URL/health"
curl -s $WEBHOOK_URL/health
echo ""
echo ""

echo -e "${GREEN}✓ DEPLOYMENT SUCCESSFUL!${NC}"
echo ""
echo "📝 Next Steps:"
echo "1. Copy the webhook URL above"
echo "2. Go to TradingView → Alerts"
echo "3. Edit BULLISH and BEARISH alerts"
echo "4. Update webhook URL in alert actions"
echo "5. Test by firing a signal"
echo ""
echo "💰 Cost: COMPLETELY FREE (Google Cloud Free Tier)"
echo "📊 Free: 2M requests/month"
echo ""
