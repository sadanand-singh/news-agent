import yaml from 'js-yaml';
import fs from 'fs';
import path from 'path';

export interface NewsItem {
    published_date: string;
    sources: string[];
    summary: string;
    title: string;
    groups?: string[]; // Add groups property to track which groups this item belongs to
}

export interface NewsGroup {
    groups: string[];
    news: NewsItem[];
}

export interface NewsCollection {
    [key: string]: NewsGroup;
}

export interface GroupedNews {
    [groupName: string]: NewsItem[];
}

export function slugify(text: string): string {
    return text.toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '') // Remove special characters except hyphens and spaces
        .replace(/[\s_-]+/g, '-') // Replace spaces, underscores, and multiple hyphens with single hyphen
        .replace(/^-+|-+$/g, ''); // Remove leading and trailing hyphens
}

function isGenericSource(url: string): boolean {
    const genericDomains = [
        'wikipedia.org',
        'medium.com'
    ];

    return genericDomains.some(domain => url.includes(domain));
}

function hasOnlyGenericSources(sources: string[]): boolean {
    // If there are no sources, consider it invalid
    if (sources.length === 0) return true;

    // Check if ALL sources are from generic sites
    return sources.every(source => isGenericSource(source));
}

function filterGenericNews(newsCollection: NewsCollection): NewsCollection {
    const filtered: NewsCollection = {};

    Object.entries(newsCollection).forEach(([topicName, topicData]) => {
        // Filter out news items that have only generic sources
        const filteredNews = topicData.news.filter(newsItem =>
            !hasOnlyGenericSources(newsItem.sources)
        );

        // Only include the topic if it has remaining news items
        if (filteredNews.length > 0) {
            filtered[topicName] = {
                ...topicData,
                news: filteredNews
            };
        }
    });

    return filtered;
}

export function loadNewsData(): NewsCollection {
    try {
        // Load the news.yaml file from the data directory
        const dataDir = path.join(process.cwd(), 'src', 'data');
        const filePath = path.join(dataDir, 'news.yaml');
        const fileContents = fs.readFileSync(filePath, 'utf8');
        const data = yaml.load(fileContents) as NewsCollection;

        // Filter out news items with only generic sources
        return filterGenericNews(data);
    } catch (error) {
        console.error('Error loading news data:', error);
        return {};
    }
}

export function getFilteredGroups(newsCollection: NewsCollection): { [groupName: string]: NewsGroup } {
    const ignoredGroups = [
        'recent events',
        'latest news',
        'breaking news',
        'recent developments',
        'politics'
    ];

    const filteredData: { [groupName: string]: NewsGroup } = {};

    Object.entries(newsCollection).forEach(([groupName, groupData]) => {
        // Filter out groups that contain ignored keywords
        const validGroups = groupData.groups.filter(group =>
            !ignoredGroups.some(ignored =>
                group.toLowerCase().includes(ignored.toLowerCase())
            )
        );

        if (validGroups.length > 0) {
            filteredData[groupName] = {
                ...groupData,
                groups: validGroups
            };
        }
    });

    return filteredData;
}

export function getAllUniqueGroups(newsCollection: NewsCollection): string[] {
    const ignoredGroups = [
        'recent events',
        'latest news',
        'breaking news',
        'recent developments'
    ];

    const allGroups = new Set<string>();

    Object.values(newsCollection).forEach(groupData => {
        groupData.groups.forEach(group => {
            if (!ignoredGroups.some(ignored =>
                group.toLowerCase().includes(ignored.toLowerCase())
            )) {
                allGroups.add(group);
            }
        });
    });

    return Array.from(allGroups).sort();
}

export function getNewsByGroups(newsCollection: NewsCollection): GroupedNews {
    const ignoredGroups = [
        'recent events',
        'latest news',
        'breaking news',
        'recent developments'
    ];

    const groupedNews: GroupedNews = {};
    const itemGroupMap = new Map<string, Set<string>>(); // Track which groups each item belongs to

    Object.values(newsCollection).forEach(topicData => {
        // Get valid groups for this topic
        const validGroups = topicData.groups.filter(group =>
            !ignoredGroups.some(ignored =>
                group.toLowerCase().includes(ignored.toLowerCase())
            )
        );

        // Add news items to each valid group
        validGroups.forEach(group => {
            if (!groupedNews[group]) {
                groupedNews[group] = [];
            }

            // Clone items and add group information
            topicData.news.forEach(item => {
                const itemKey = `${item.title}-${item.published_date}`;

                // Track groups for this item
                if (!itemGroupMap.has(itemKey)) {
                    itemGroupMap.set(itemKey, new Set());
                }
                itemGroupMap.get(itemKey)!.add(group);

                // Check if item already exists in this group
                const existingItem = groupedNews[group].find(existing =>
                    existing.title === item.title && existing.published_date === item.published_date
                );

                if (!existingItem) {
                    const itemWithGroups = {
                        ...item,
                        groups: Array.from(itemGroupMap.get(itemKey)!)
                    };
                    groupedNews[group].push(itemWithGroups);
                } else {
                    // Update existing item with all groups
                    existingItem.groups = Array.from(itemGroupMap.get(itemKey)!);
                }
            });
        });
    });

    // Sort news within each group by date (newest first)
    Object.keys(groupedNews).forEach(group => {
        groupedNews[group].sort((a, b) => {
            const dateA = new Date(a.published_date);
            const dateB = new Date(b.published_date);

            // Handle invalid dates by putting them at the end
            if (isNaN(dateA.getTime()) && isNaN(dateB.getTime())) return 0;
            if (isNaN(dateA.getTime())) return 1;
            if (isNaN(dateB.getTime())) return -1;

            // Sort by newest first (descending order)
            return dateB.getTime() - dateA.getTime();
        });
    });

    return groupedNews;
} 