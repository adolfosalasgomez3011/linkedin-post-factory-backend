# LinkedIn Post Factory - Deployment URLs

## Production URLs

### Frontend (Vercel)
```
https://linkedin-post-rho.vercel.app/
```

### Backend API (Render)
```
https://linkedin-post-factory-backend.onrender.com
```

### API Documentation
```
https://linkedin-post-factory-backend.onrender.com/docs
```

### Health Check
```
https://linkedin-post-factory-backend.onrender.com/health
```

## Database (Supabase)

### Project URL
```
https://nvmwbkfgerflntguvguj.supabase.co
```

### Dashboard
```
https://supabase.com/dashboard/project/nvmwbkfgerflntguvguj
```

## GitHub Repository

### Backend
```
https://github.com/adolfosalasgomez3011/linkedin-post-factory-backend
```

## Important Notes

- **Backend on Render Free Tier**: Spins down after 15 minutes of inactivity, first request after sleep takes ~30 seconds
- **Frontend on Vercel**: Always available, no sleep time
- **Database on Supabase**: Free tier, always active

## Next Steps to Complete Setup

1. Go to Vercel Dashboard: https://vercel.com/dashboard
2. Select project: `linkedin-post-rho`
3. Settings → Environment Variables
4. Add: `NEXT_PUBLIC_API_URL` = `https://linkedin-post-factory-backend.onrender.com`
5. Redeploy the frontend

---
Created: January 25, 2026
