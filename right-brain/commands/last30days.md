# /last30days — Multi-Platform Social Research

Search 8 platforms in parallel, rank results by social signal, and synthesize into one brief.

## Usage
```
/last30days <topic>
/last30days Dave Morin
/last30days Apple M5 Pro
/last30days CLI vs MCP
```

## Sources (searched in parallel)
1. **Reddit** — upvotes, comment depth
2. **X / Twitter** — likes, retweets, quote tweets
3. **YouTube** — views, engagement
4. **TikTok** — views, likes, shares
5. **Instagram Reels** — reach, engagement
6. **Hacker News** — points, comment count
7. **Polymarket** — odds backed by real money
8. **Web** — editorial coverage, docs

## How It Works
1. Search all 8 sources for `$ARGUMENTS` content from the last 30 days
2. Score every result by social signal (upvotes, views, likes, bet amounts)
3. Synthesize the highest-signal content into one structured brief
4. Rank by **social relevancy, not SEO relevancy**

## Output Format
```markdown
## Research Brief: <topic>
## Date Range: last 30 days
## Sources Searched: 8

### Key Findings
<top 3-5 insights ranked by cross-platform signal strength>

### Platform Breakdown
#### Reddit (r/relevant_subs)
<top threads by upvotes, key quotes>

#### X / Twitter
<top posts by engagement, expert takes>

#### YouTube
<top videos by views, key insights>

#### TikTok
<top creators, viral content, view counts>

#### Instagram Reels
<creator perspectives, reach numbers>

#### Hacker News
<top threads by points, technical depth>

#### Polymarket
<relevant prediction markets, current odds>

#### Web
<editorial coverage, official announcements>

### Synthesis
<what the cross-platform signal tells you — not just what's being said, but what matters based on real engagement>

### Ready to Act
<offer to apply the research — write a plan, draft a design, prepare talking points, etc.>
```

## Instructions
1. Use web search to find recent content across all 8 platforms for `$ARGUMENTS`
2. For each result, note the social signal (upvotes, views, likes, points, odds)
3. Weight results by engagement — a Reddit thread with 1500 upvotes matters more than a blog post nobody read
4. Synthesize across platforms — find the story that emerges from the intersection of all sources
5. End by offering to apply the research to the user's actual task
