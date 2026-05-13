@echo off
:: Voice Corpus Auto-Uploader
:: Watches PublishedPost_MachineLearnign and uploads any new PDF to Supabase + Neon
cd /d "C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\Post_Factory_App"
python upload_voice_corpus.py --watch
