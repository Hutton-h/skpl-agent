import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Store, TrendingUp, Search, Users, Edit, Target, BarChart3, BookOpen, Share2, Sparkles, Plus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { getBaseUrl, getToken } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// ── Types ────────────────────────────────────────────────────────────────────

interface TemplateCategory {
  name: string;
  name_en: string;
}

interface AgentTemplate {
  id: string;
  name: string;
  name_en: string;
  description: string;
  category: string;
  icon: string;
  tools: string[];
  tags: string[];
  version: string;
}

interface TemplatesResponse {
  templates: AgentTemplate[];
  categories: Record<string, TemplateCategory>;
  total: number;
}

// ── API ──────────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getBaseUrl();
  const token = getToken();
  const url = baseUrl ? `${baseUrl}${path}` : path;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Icon mapping ─────────────────────────────────────────────────────────────

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'trending-up': TrendingUp,
  'search': Search,
  'users': Users,
  'edit': Edit,
  'target': Target,
  'bar-chart': BarChart3,
  'book-open': BookOpen,
  'share': Share2,
};

function getIcon(iconName: string) {
  const Icon = iconMap[iconName] || Sparkles;
  return Icon;
}

const categoryColorMap: Record<string, string> = {
  research: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  seo: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  sales: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  content: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  data: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
};

// ── Template Card ────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  onSelect,
}: {
  template: AgentTemplate;
  onSelect: (t: AgentTemplate) => void;
}) {
  const { i18n } = useTranslation();
  const isZh = i18n.language.startsWith('zh');
  const Icon = getIcon(template.icon);
  const colorClass = categoryColorMap[template.category] || 'bg-gray-100 text-gray-700';

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer group" onClick={() => onSelect(template)}>
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className={`p-2.5 rounded-lg shrink-0 ${colorClass}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-base truncate">
              {isZh ? template.name : template.name_en}
            </h3>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {template.description}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {template.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {template.tags.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{template.tags.length - 3}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
              <span>{template.tools.length} tools</span>
              <span>·</span>
              <span>v{template.version}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function AgentMarketPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const isZh = i18n.language.startsWith('zh');

  const [templates, setTemplates] = useState<AgentTemplate[]>([]);
  const [categories, setCategories] = useState<Record<string, TemplateCategory>>({});
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplate | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchTemplates = useCallback(async (category?: string | null) => {
    setLoading(true);
    try {
      const params = category ? `?category=${category}` : '';
      const data = await apiFetch<TemplatesResponse>(`/api/agent-templates${params}`);
      setTemplates(data.templates);
      setCategories(data.categories);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates(selectedCategory);
  }, [selectedCategory, fetchTemplates]);

  const handleCreateFromTemplate = async () => {
    if (!selectedTemplate) return;
    setCreating(true);
    try {
      const result = await apiFetch<{ agent_id: string; name: string }>(
        `/api/agent-templates/${selectedTemplate.id}/create`,
        { method: 'POST' },
      );
      toast.success(t('agentMarket.created', { name: result.name }));
      setSelectedTemplate(null);
      navigate(`/chat/${result.agent_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('agentMarket.createFailed'));
    } finally {
      setCreating(false);
    }
  };

  const allLabel = t('agentMarket.allCategories') || 'All';

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Store className="h-6 w-6" />
            {t('agentMarket.title')}
          </h1>
          <p className="text-muted-foreground mt-1">{t('agentMarket.subtitle')}</p>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <Badge
          variant={selectedCategory === null ? 'default' : 'outline'}
          className="cursor-pointer px-3 py-1.5"
          onClick={() => setSelectedCategory(null)}
        >
          {allLabel} ({templates.length})
        </Badge>
        {Object.entries(categories).map(([key, cat]) => (
          <Badge
            key={key}
            variant={selectedCategory === key ? 'default' : 'outline'}
            className="cursor-pointer px-3 py-1.5"
            onClick={() => setSelectedCategory(selectedCategory === key ? null : key)}
          >
            {isZh ? cat.name : cat.name_en}
          </Badge>
        ))}
      </div>

      {/* Templates grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Store className="h-12 w-12 mb-3" />
            <p className="text-lg font-medium">{t('agentMarket.noTemplates')}</p>
            <p className="text-sm mt-1">{t('agentMarket.noTemplatesDesc')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((tmpl) => (
            <TemplateCard
              key={tmpl.id}
              template={tmpl}
              onSelect={setSelectedTemplate}
            />
          ))}
        </div>
      )}

      {/* Template Detail Dialog */}
      <Dialog
        open={selectedTemplate !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedTemplate(null);
        }}
      >
        <DialogContent className="max-w-lg">
          {selectedTemplate && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  {(() => {
                    const Icon = getIcon(selectedTemplate.icon);
                    return <Icon className="h-5 w-5" />;
                  })()}
                  {isZh ? selectedTemplate.name : selectedTemplate.name_en}
                </DialogTitle>
                <DialogDescription>{selectedTemplate.description}</DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Tools */}
                <div>
                  <h4 className="text-sm font-medium mb-2">{t('agentMarket.tools')}</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedTemplate.tools.map((tool) => (
                      <Badge key={tool} variant="secondary" className="text-xs font-mono">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Tags */}
                <div>
                  <h4 className="text-sm font-medium mb-2">{t('agentMarket.tags')}</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedTemplate.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Version */}
                <div className="text-xs text-muted-foreground">
                  v{selectedTemplate.version}
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setSelectedTemplate(null)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={handleCreateFromTemplate} disabled={creating}>
                  {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  <Plus className="h-4 w-4 mr-1" />
                  {t('agentMarket.createAgent')}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}