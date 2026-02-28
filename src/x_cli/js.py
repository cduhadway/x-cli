"""JavaScript injection strings for tweet extraction."""

EXTRACT_TWEETS_JS = """() => {
    const extractLinks = (container) => {
        const links = [];
        const seen = new Set();
        for (const a of container.querySelectorAll('a[href]')) {
            const href = a.href;
            if (!href || href.startsWith('https://x.com') || href.startsWith('https://twitter.com')) continue;
            const text = a.innerText.trim().substring(0, 300);
            const key = href + '|' + text;
            if (seen.has(key)) continue;
            seen.add(key);
            links.push({href, text});
        }
        return links;
    };
    const tweets = [];
    for (const article of document.querySelectorAll('article[data-testid="tweet"]')) {
        try {
            const allTexts = article.querySelectorAll('[data-testid="tweetText"]');
            const text = allTexts.length > 0 ? allTexts[0].innerText : '';
            const links = extractLinks(article);
            let quotedText = '', quotedUser = '', quotedUrl = '';
            for (const inner of article.querySelectorAll('[role="link"][tabindex="0"]')) {
                const h = inner.getAttribute('href') || '';
                if (h.includes('/status/')) {
                    quotedUrl = 'https://x.com' + h;
                    const qt = inner.querySelector('[data-testid="tweetText"]');
                    if (qt) quotedText = qt.innerText;
                    break;
                }
            }
            if (!quotedText && allTexts.length > 1) quotedText = allTexts[1].innerText;
            const timeEl = article.querySelector('time');
            const userEl = article.querySelector('[data-testid="User-Name"]');
            const permalink = article.querySelector('a[href*="/status/"]');
            // Detect "Show more" truncation — Twitter hides links in collapsed long tweets
            const showMore = article.querySelector('[data-testid="tweet-text-show-more-link"]');
            tweets.push({
                text: text.substring(0, 2000),
                links,
                quoted_text: quotedText.substring(0, 2000),
                quoted_user: quotedUser,
                quoted_url: quotedUrl,
                timestamp: timeEl ? timeEl.getAttribute('datetime') : null,
                user_name: userEl ? userEl.innerText.split('\\n')[0] : '',
                user_handle: userEl ? (userEl.innerText.match(/@\\w+/) || [''])[0] : '',
                tweet_url: permalink ? permalink.href : '',
                truncated: !!showMore,
            });
        } catch (e) {}
    }
    return tweets;
}"""

EXTRACT_SINGLE_TWEET_LINKS_JS = """() => {
    const article = document.querySelector('article[data-testid="tweet"]');
    if (!article) return {links: [], text: ''};
    const links = [];
    const seen = new Set();
    for (const a of article.querySelectorAll('a[href]')) {
        const href = a.href;
        if (!href || href.startsWith('https://x.com') || href.startsWith('https://twitter.com')) continue;
        const text = a.innerText.trim().substring(0, 300);
        const key = href + '|' + text;
        if (seen.has(key)) continue;
        seen.add(key);
        links.push({href, text});
    }
    const textEl = article.querySelector('[data-testid="tweetText"]');
    return {links, text: textEl ? textEl.innerText.substring(0, 2000) : ''};
}"""

EXTRACT_THREAD_JS = """(handle) => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    const links = [];
    const texts = [];
    const seen = new Set();
    for (const article of articles) {
        const userEl = article.querySelector('[data-testid="User-Name"]');
        if (!userEl) continue;
        const articleHandle = (userEl.innerText.match(/@\\w+/) || [''])[0].toLowerCase();
        if (articleHandle !== handle.toLowerCase()) continue;
        const textEl = article.querySelector('[data-testid="tweetText"]');
        if (textEl) texts.push(textEl.innerText.substring(0, 2000));
        for (const a of article.querySelectorAll('a[href]')) {
            const href = a.href;
            if (!href || href.startsWith('https://x.com') || href.startsWith('https://twitter.com')) continue;
            const text = a.innerText.trim().substring(0, 300);
            const key = href + '|' + text;
            if (seen.has(key)) continue;
            seen.add(key);
            links.push({href, text});
        }
    }
    return {links, texts};
}"""
