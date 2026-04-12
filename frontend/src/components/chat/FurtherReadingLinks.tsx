/**
 * FurtherReadingLinks — Styled link chips for theory answers (Section 8).
 * Renders markdown links as clickable, styled chips that open in new tabs.
 */
import { ExternalLink } from 'lucide-react';

interface Props {
  /** Raw markdown text that may contain links like [Title](URL) */
  content: string;
}

interface ParsedLink {
  title: string;
  url: string;
  domain: string;
}

function extractLinks(text: string): ParsedLink[] {
  const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  const links: ParsedLink[] = [];
  let match;

  while ((match = linkRegex.exec(text)) !== null) {
    const url = match[2];
    let domain = '';
    try {
      domain = new URL(url).hostname.replace('www.', '');
    } catch {
      domain = url;
    }
    links.push({ title: match[1], url, domain });
  }

  return links;
}

const domainColors: Record<string, string> = {
  'sbp.org.pk': '#00D4AA',
  'psx.com.pk': '#22C55E',
  'investopedia.com': '#3B82F6',
  'nbp.com.pk': '#EAB308',
  'imf.org': '#8B5CF6',
  'worldbank.org': '#F97316',
};

export default function FurtherReadingLinks({ content }: Props) {
  const links = extractLinks(content);

  if (links.length === 0) return null;

  return (
    <div className="further-reading">
      <div className="further-reading-title">📚 Further Reading</div>
      <div className="further-reading-chips">
        {links.map((link, i) => {
          const color = domainColors[link.domain] || 'var(--accent)';
          return (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="reading-chip"
              style={{ borderColor: color }}
            >
              <span className="reading-chip-dot" style={{ background: color }} />
              <span className="reading-chip-title">{link.title}</span>
              <span className="reading-chip-domain">{link.domain}</span>
              <ExternalLink size={11} />
            </a>
          );
        })}
      </div>
    </div>
  );
}
