-- story_tracking_schema.sql
-- Schema for story tracking feature

-- Table for tracked stories
CREATE TABLE tracked_stories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  keyword VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_updated TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Table for articles related to tracked stories
CREATE TABLE tracked_story_articles (
  tracked_story_id UUID REFERENCES tracked_stories(id) ON DELETE CASCADE,
  news_id UUID REFERENCES news_articles(id) ON DELETE CASCADE,
  added_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tracked_story_id, news_id)
);

-- Index for faster lookups
CREATE INDEX idx_tracked_stories_user_id ON tracked_stories(user_id);
CREATE INDEX idx_tracked_stories_keyword ON tracked_stories(keyword);
CREATE INDEX idx_tracked_story_articles_story_id ON tracked_story_articles(tracked_story_id);

-- RLS Policies for tracked_stories
ALTER TABLE tracked_stories ENABLE ROW LEVEL SECURITY;

-- Allow users to view only their own tracked stories
CREATE POLICY tracked_stories_select_policy ON tracked_stories 
  FOR SELECT USING (auth.uid() = user_id);

-- Allow users to insert their own tracked stories
CREATE POLICY tracked_stories_insert_policy ON tracked_stories 
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Allow users to update only their own tracked stories
CREATE POLICY tracked_stories_update_policy ON tracked_stories 
  FOR UPDATE USING (auth.uid() = user_id);

-- Allow users to delete only their own tracked stories
CREATE POLICY tracked_stories_delete_policy ON tracked_stories 
  FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for tracked_story_articles
ALTER TABLE tracked_story_articles ENABLE ROW LEVEL SECURITY;

-- Allow users to view only articles related to their tracked stories
CREATE POLICY tracked_story_articles_select_policy ON tracked_story_articles 
  FOR SELECT USING (
    tracked_story_id IN (
      SELECT id FROM tracked_stories WHERE user_id = auth.uid()
    )
  );

-- Allow users to insert only articles related to their tracked stories
CREATE POLICY tracked_story_articles_insert_policy ON tracked_story_articles 
  FOR INSERT WITH CHECK (
    tracked_story_id IN (
      SELECT id FROM tracked_stories WHERE user_id = auth.uid()
    )
  );

-- Allow users to delete only articles related to their tracked stories
CREATE POLICY tracked_story_articles_delete_policy ON tracked_story_articles 
  FOR DELETE USING (
    tracked_story_id IN (
      SELECT id FROM tracked_stories WHERE user_id = auth.uid()
    )
  );