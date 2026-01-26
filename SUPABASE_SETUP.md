# Supabase Setup Guide

## Step 1: Create Tables in Supabase

1. Go to your Supabase project: https://app.supabase.com/project/nelzfeoznjuewtnibelt
2. Click **SQL Editor** in the left sidebar
3. Click **New query**
4. Copy and paste the entire contents of `database_schema.sql`
5. Click **Run** (or press Ctrl+Enter)

You should see: "Success. No rows returned"

## Step 2: Verify Tables Created

In SQL Editor, run:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('posts', 'engagement');
```

You should see:
- posts
- engagement

## Step 3: Test Connection

Run the test script:
```bash
python Post_Factory/core/database_supabase.py
```

## Step 4: Start API with Supabase

The API is now configured to use Supabase instead of SQLite!

```bash
cd Post_Factory
start_api.bat
```

## Benefits of Supabase

✅ **Cloud storage** - Access from anywhere
✅ **Real-time** - Updates sync instantly
✅ **Scalable** - Handles growth automatically
✅ **Backup** - Automatic backups
✅ **PostgreSQL** - Powerful queries
✅ **Dashboard** - View data in Supabase UI

## View Your Data

Go to: https://app.supabase.com/project/nelzfeoznjuewtnibelt/editor

Click **posts** table to see all your generated posts!

## API Endpoints (Same as Before)

- `POST /posts/generate` - Generate post (saves to Supabase)
- `GET /posts` - List posts (from Supabase)
- `PUT /posts/{id}` - Update post
- `DELETE /posts/{id}` - Delete post

All data now stored in the cloud! 🚀
