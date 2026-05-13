# Quick Start Guide

## Prerequisites Checklist

Before running the app, make sure you have:

- [ ] Node.js 20 or higher installed
- [ ] A Supabase account ([supabase.com](https://supabase.com))
- [ ] Backend API running (separate Python FastAPI server)

## Setup Steps

### 1. Install Dependencies

```bash
npm install
```

### 2. Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Once your project is ready, go to **Settings** → **API**
3. Copy your **Project URL** and **anon/public key**
4. In the Supabase dashboard, go to the **SQL Editor**
5. Copy the contents of `supabase-schema.sql` and run it
6. Verify tables were created: Check **Table Editor** to see `posts` and `engagement` tables

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.local.example .env.local

# Edit .env.local with your actual credentials
# Required variables:
# - NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
# - NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
# - NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Start the Development Server

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

## Verify Setup

### Test Database Connection

1. Open the app at http://localhost:3000
2. Click on the **Library** tab
3. You should see "No posts found" (not an error - this means Supabase is connected!)

### Test Post Generation

1. Make sure your **backend API is running** (usually on port 8000)
2. Go to the **Generate** tab
3. Select a Content Pillar and Format
4. Click "Generate Post"
5. If successful, you'll see the generated post in the preview area

## Common Issues

### "Failed to generate post" Error

**Problem**: Backend API is not running or not accessible

**Solution**: 
- Check if the backend server is running on port 8000
- Verify `NEXT_PUBLIC_API_URL` in `.env.local` matches your backend URL
- Make sure you have the backend repository set up

### No Posts Showing in Library

**Problem**: Supabase connection issue

**Solution**:
- Verify your Supabase credentials in `.env.local`
- Check that you ran the `supabase-schema.sql` script
- Look in the browser console for error messages

### Blank Page or Error on Load

**Problem**: Missing environment variables

**Solution**:
- Make sure `.env.local` exists and has all required variables
- Restart the dev server after adding environment variables
- Check for typos in variable names (must start with `NEXT_PUBLIC_`)

## Project Structure

```
post-app/
├── app/                      # Next.js app directory
│   ├── page.tsx             # Main dashboard (tabs: Generate, Library, Analytics)
│   ├── layout.tsx           # Root layout with metadata
│   └── globals.css          # Global styles
├── components/              # React components
│   ├── ui/                 # Shadcn UI components (buttons, cards, etc.)
│   ├── post-generator.tsx  # Post generation interface
│   ├── post-library.tsx    # Post management & editing
│   └── analytics.tsx       # Statistics & charts
├── lib/                     # Utilities
│   ├── api.ts              # Backend API client functions
│   ├── supabase.ts         # Supabase client & database functions
│   └── utils.ts            # Helper utilities
└── types/                   # TypeScript definitions
    └── database.ts         # Supabase database types
```

## Next Steps

Once everything is running:

1. **Generate Your First Post**:
   - Go to Generate tab
   - Select "AI & Innovation" as pillar
   - Choose "Story" format
   - Click "Generate Post"

2. **Manage Your Posts**:
   - Switch to Library tab
   - Edit, update status, or delete posts
   - Use search and filters to organize

3. **View Analytics**:
   - Go to Analytics tab
   - See distribution by pillar and format
   - Track your content strategy

## Getting Help

- Check the main README.md for detailed documentation
- Review `supabase-schema.sql` for database structure
- Look at component files for API usage examples

## Development Tips

- The app uses Tailwind CSS for styling
- UI components are from Shadcn UI (Radix primitives)
- All API calls go through the backend server
- Direct database operations use Supabase client
- Changes auto-reload in development mode

Happy posting! 🚀
