# 🚀 Deploy Backend & Fix Vercel Frontend

## The Problem
Your Vercel frontend at https://linkedin-post-rho.vercel.app/ is failing because:
- It's trying to call `http://localhost:8000` (your local backend)
- Localhost doesn't exist in production - it only works on your computer
- You need to deploy the backend to a cloud service

## Solution: Deploy Backend to Render.com (Free Tier)

### Step 1: Prepare for Deployment

1. **Create a GitHub repository** (if you haven't already):
   ```bash
   cd "C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\Post_Factory"
   git init
   git add .
   git commit -m "Initial commit - LinkedIn Post Factory Backend"
   ```

2. **Push to GitHub**:
   - Go to https://github.com/new
   - Create a new repository called `linkedin-post-factory-backend`
   - Run:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/linkedin-post-factory-backend.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy to Render.com

1. **Sign up** at https://render.com (free account)

2. **Create a New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select `linkedin-post-factory-backend`

3. **Configure the service**:
   - **Name**: `linkedin-post-factory-api`
   - **Region**: Choose closest to you (e.g., Oregon for US West)
   - **Branch**: `main`
   - **Root Directory**: Leave blank
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`

4. **Add Environment Variables** (in Render dashboard):
   Click "Environment" and add these:
   
   | Key | Value |
   |-----|-------|
   | `GOOGLE_API_KEY` | `AIzaSyBD8lYwIWGSQ0v9b6WVxcM39sROMeZh_8U` |
   | `ANTHROPIC_API_KEY` | (your Anthropic key if you have one) |
   | `OPENAI_API_KEY` | (your OpenAI key if you have one) |
   | `SUPABASE_URL` | (from your Supabase project) |
   | `SUPABASE_KEY` | (from your Supabase project) |
   | `PYTHON_VERSION` | `3.11.0` |

5. **Deploy**:
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment
   - You'll get a URL like: `https://linkedin-post-factory-api.onrender.com`

### Step 3: Update Vercel Frontend

1. **Go to Vercel Dashboard**: https://vercel.com/dashboard

2. **Select your project**: `linkedin-post-rho`

3. **Go to Settings** → **Environment Variables**

4. **Add the environment variable**:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://linkedin-post-factory-api.onrender.com` (your Render URL)
   - **Environment**: Production, Preview, Development (select all)
   - Click "Save"

5. **Redeploy**:
   - Go to "Deployments" tab
   - Click the three dots on the latest deployment
   - Click "Redeploy"
   - Wait 2-3 minutes

### Step 4: Verify It Works

1. **Test the backend**:
   - Visit: `https://linkedin-post-factory-api.onrender.com/health`
   - You should see: `{"status":"healthy","timestamp":"..."}`

2. **Test the frontend**:
   - Visit: https://linkedin-post-rho.vercel.app/
   - Try generating a post
   - Should work now! 🎉

## Alternative: Quick Fix for Testing Only

If you just want to test locally and don't want to deploy yet:

1. **Make sure backend is running locally**:
   - Double-click `C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\Post_Factory\start_api.bat`
   - Wait for "Uvicorn running on http://0.0.0.0:8000"

2. **The Vercel app will still fail** because it can't reach your local machine

## Troubleshooting

### Render deployment fails
- Check "Logs" in Render dashboard
- Make sure `requirements.txt` has all dependencies
- Verify environment variables are set

### Frontend still shows error
- Make sure you redeployed after adding environment variable
- Check browser console (F12) for error messages
- Verify the backend URL is correct (no trailing slash)

### CORS errors
- The backend already has CORS enabled for all origins
- If issues persist, update `api/main.py` CORS settings

## What About the Gemini Image MCP?

The MCP server (`gemini-imagen`) you have in VS Code is **local only** - it can't be used by the deployed app. Instead:

1. Your backend (`api/services/media_generator.py`) already uses the Gemini API directly
2. It doesn't need the MCP - it uses the `GOOGLE_API_KEY` environment variable
3. Once deployed to Render, it will work automatically

The MCP was useful for testing in VS Code, but the production app uses the direct API.

## Cost

- **Render Free Tier**: Free forever (spins down after 15 min of inactivity)
- **Vercel Free Tier**: Free forever (100GB bandwidth/month)
- **Gemini API**: Free quota (1500 requests/day)

Total cost: **$0/month** 🎉

---

Need help? Check:
- Render logs: https://dashboard.render.com → Your service → Logs
- Vercel logs: https://vercel.com/dashboard → Your project → Deployments → View Function Logs
