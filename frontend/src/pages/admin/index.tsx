import { useEffect, useState } from 'react';
import { Shield, Cpu, LibraryBig, Users, ScanSearch, Plus, Pencil, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { getBaseUrl, getToken } from '@/api/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';

// ── Types ────────────────────────────────────────────────────────────────────

interface VectorConfig {
  provider: string;
  api_key: string;
  base_url: string;
  model: string;
  dimensions: number;
}

interface KnowledgeBaseItem {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  created_at: string;
}

interface UserItem {
  id: string;
  username: string;
  email: string;
  role: string;
  created_at: string;
  last_login_at: string;
}


interface ShieldScanResult {
  agent_name: string;
  risk_level: string;
  total_findings: number;
  passed: boolean;
  summary: Record<string, number>;
  findings: Array<{
    rule_id: string;
    category: string;
    description: string;
    severity: string;
    evidence: string;
    recommendation: string;
  }>;
}

// ── API helpers ──────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const baseUrl = getBaseUrl();
  const token = getToken();
  const url = baseUrl ? `${baseUrl}${path}` : path;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Vector Config Form ───────────────────────────────────────────────────────

function VectorConfigTab() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [config, setConfig] = useState<VectorConfig>({
    provider: 'openai',
    api_key: '',
    base_url: '',
    model: '',
    dimensions: 1536,
  });

  useEffect(() => {
    async function fetchConfig() {
      try {
        const data = await apiFetch<VectorConfig>('/api/admin/vector-config');
        setConfig(data);
      } catch {
        // Use defaults if config not yet set
      } finally {
        setFetching(false);
      }
    }
    fetchConfig();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiFetch('/api/admin/vector-config', {
        method: 'PUT',
        body: JSON.stringify(config),
      });
      toast.success(t('admin.vectorConfig.configSaved'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.vectorConfig.saveFailed'));
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-4 w-4" />
            {t('admin.vectorConfig.title')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Provider */}
          <div className="space-y-2">
            <Label htmlFor="provider">{t('admin.vectorConfig.provider')}</Label>
            <Select
              value={config.provider}
              onValueChange={(value) =>
                setConfig((prev) => ({ ...prev, provider: value }))
              }
            >
              <SelectTrigger id="provider" className="w-full">
                <SelectValue placeholder={t('admin.vectorConfig.selectProvider')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="ollama">Ollama</SelectItem>
                <SelectItem value="voyageai">VoyageAI</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api-key">{t('admin.vectorConfig.apiKey')}</Label>
            <Input
              id="api-key"
              type="password"
              placeholder={t('admin.vectorConfig.enterApiKey')}
              value={config.api_key}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, api_key: e.target.value }))
              }
            />
          </div>

          {/* Base URL */}
          <div className="space-y-2">
            <Label htmlFor="base-url">{t('admin.vectorConfig.baseUrl')}</Label>
            <Input
              id="base-url"
              type="text"
              placeholder="https://api.openai.com/v1"
              value={config.base_url}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, base_url: e.target.value }))
              }
            />
          </div>

          {/* Model */}
          <div className="space-y-2">
            <Label htmlFor="model">{t('admin.vectorConfig.model')}</Label>
            <Input
              id="model"
              type="text"
              placeholder="text-embedding-3-small"
              value={config.model}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, model: e.target.value }))
              }
            />
          </div>

          {/* Dimensions */}
          <div className="space-y-2">
            <Label htmlFor="dimensions">{t('admin.vectorConfig.dimensions')}</Label>
            <Input
              id="dimensions"
              type="number"
              placeholder="1536"
              value={config.dimensions}
              onChange={(e) =>
                setConfig((prev) => ({
                  ...prev,
                  dimensions: parseInt(e.target.value) || 0,
                }))
              }
            />
          </div>
        </CardContent>
      </Card>

      <Button type="submit" disabled={loading}>
        {loading && <Spinner className="h-4 w-4 mr-2" />}
        {t('admin.vectorConfig.saveConfig')}
      </Button>
    </form>
  );
}

// ── Knowledge Base Management Tab ────────────────────────────────────────────

function KnowledgeBaseTab() {
  const { t } = useTranslation();
  const [items, setItems] = useState<KnowledgeBaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBaseItem | null>(null);
  const [editingItem, setEditingItem] = useState<KnowledgeBaseItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });

  const fetchItems = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<KnowledgeBaseItem[]>('/api/admin/knowledge-bases');
      setItems(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.knowledgeBases.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const openCreate = () => {
    setEditingItem(null);
    setForm({ name: '', description: '' });
    setDialogOpen(true);
  };

  const openEdit = (item: KnowledgeBaseItem) => {
    setEditingItem(item);
    setForm({ name: item.name, description: item.description });
    setDialogOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingItem) {
        await apiFetch(`/api/admin/knowledge-bases/${editingItem.id}`, {
          method: 'PUT',
          body: JSON.stringify(form),
        });
        toast.success(t('admin.knowledgeBases.updated'));
      } else {
        await apiFetch('/api/admin/knowledge-bases', {
          method: 'POST',
          body: JSON.stringify(form),
        });
        toast.success(t('admin.knowledgeBases.created'));
      }
      setDialogOpen(false);
      fetchItems();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.knowledgeBases.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiFetch(`/api/admin/knowledge-bases/${deleteTarget.id}`, {
        method: 'DELETE',
      });
      toast.success(t('admin.knowledgeBases.deleted'));
      setDeleteTarget(null);
      fetchItems();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.knowledgeBases.deleteFailed'));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t('admin.knowledgeBases.title')}</h3>
        <Button onClick={openCreate} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          {t('admin.knowledgeBases.create')}
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <LibraryBig className="h-10 w-10 mb-2" />
            <p>{t('admin.knowledgeBases.noKnowledgeBases')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.id} size="sm">
              <CardContent className="flex items-center justify-between py-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{item.name}</span>
                    {item.is_public && (
                      <Badge variant="secondary">{t('admin.knowledgeBases.public')}</Badge>
                    )}
                  </div>
                  {item.description && (
                    <p className="text-sm text-muted-foreground truncate mt-0.5">
                      {item.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-4 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => openEdit(item)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setDeleteTarget(item)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingItem ? t('admin.knowledgeBases.edit') : t('admin.knowledgeBases.createNew')}
            </DialogTitle>
            <DialogDescription>
              {editingItem
                ? t('admin.knowledgeBases.editDesc')
                : t('admin.knowledgeBases.createDesc')}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="kb-name">{t('admin.knowledgeBases.name')}</Label>
              <Input
                id="kb-name"
                value={form.name}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, name: e.target.value }))
                }
                required
                placeholder={t('admin.knowledgeBases.namePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kb-desc">{t('admin.knowledgeBases.description')}</Label>
              <Input
                id="kb-desc"
                value={form.description}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder={t('admin.knowledgeBases.descriptionPlaceholder')}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                {t('admin.knowledgeBases.cancel')}
              </Button>
              <Button type="submit" disabled={saving}>
                {saving && <Spinner className="h-4 w-4 mr-2" />}
                {editingItem ? t('admin.knowledgeBases.update') : t('admin.knowledgeBases.create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.knowledgeBases.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('admin.knowledgeBases.deleteDesc', { name: deleteTarget?.name ?? '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              {t('admin.knowledgeBases.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              {t('admin.knowledgeBases.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── User List Tab ────────────────────────────────────────────────────────────

function UsersTab() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<UserItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<UserItem[]>('/api/admin/users');
      setUsers(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.users.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleDeleteUser = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await apiFetch(`/api/admin/users/${deleteTarget.id}`, {
        method: 'DELETE',
      });
      toast.success(t('admin.users.deleteSuccess'));
      setDeleteTarget(null);
      fetchUsers();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('admin.users.deleteFailed'));
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{t('admin.users.title')}</h3>
      {users.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Users className="h-10 w-10 mb-2" />
            <p>{t('admin.users.noUsers')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-2.5 text-sm font-medium text-muted-foreground">
                  {t('admin.users.username')}
                </th>
                <th className="text-left px-4 py-2.5 text-sm font-medium text-muted-foreground">
                  {t('admin.users.role')}
                </th>
                <th className="text-left px-4 py-2.5 text-sm font-medium text-muted-foreground">
                  {t('admin.users.createdAt')}
                </th>
                <th className="text-left px-4 py-2.5 text-sm font-medium text-muted-foreground">
                  {t('admin.users.lastLogin')}
                </th>
                <th className="text-right px-4 py-2.5 text-sm font-medium text-muted-foreground">
                  {t('common.actions')}
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isSelf = currentUser?.username === user.username;
                const isAdmin = user.role === 'admin';
                const canDelete = !isSelf && !isAdmin;

                return (
                  <tr key={user.id} className="border-b last:border-0">
                    <td className="px-4 py-2.5 text-sm font-medium">{user.username}</td>
                    <td className="px-4 py-2.5">
                      <Badge
                        variant={isAdmin ? 'default' : 'secondary'}
                      >
                        {isAdmin ? t('admin.users.admin') : t('admin.users.user')}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-muted-foreground">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-muted-foreground">
                      {formatDate(user.last_login_at)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {canDelete ? (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setDeleteTarget(user)}
                          title={t('admin.users.deleteUser')}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground px-2">
                          {isSelf ? '-' : ''}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete User Confirmation Dialog */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin.users.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('admin.users.deleteDesc', { name: deleteTarget?.username ?? '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              {t('admin.users.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDeleteUser} disabled={deleting}>
              {deleting && <Spinner className="h-4 w-4 mr-2" />}
              {t('admin.users.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


// ── AgentShield Security Scan Tab ────────────────────────────────────────────

function AgentShieldTab() {
  const { t } = useTranslation();
  const [agents, setAgents] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [scanResult, setScanResult] = useState<ShieldScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(true);

  useEffect(() => {
    async function fetchAgents() {
      try {
        const data = await apiFetch<{ agents: Array<{ id: string; data: { name: string } }> }>('/agent/');
        const list = (data.agents || []).map((a: any) => ({
          id: a.id || a.agent_id,
          name: a.data?.name || a.name || 'Unknown',
        }));
        setAgents(list);
      } catch {
        // Silent
      } finally {
        setLoadingAgents(false);
      }
    }
    fetchAgents();
  }, []);

  const handleScan = async () => {
    if (!selectedAgent) return;
    setScanning(true);
    setScanResult(null);
    try {
      // Get agent config first
      const agentData = await apiFetch<any>(`/agent/${selectedAgent}`);
      const config = {
        name: agentData?.data?.name || agentData?.name || 'Unknown',
        system_prompt: agentData?.data?.system_prompt || agentData?.system_prompt || '',
        tools: agentData?.data?.tools || agentData?.tools || [],
        permission_mode: agentData?.data?.permission_mode || agentData?.permission_mode || 'default',
      };
      const result = await apiFetch<ShieldScanResult>('/api/shield/scan', {
        method: 'POST',
        body: JSON.stringify(config),
      });
      setScanResult(result);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const severityColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-600 bg-red-100 dark:bg-red-900/30';
      case 'high': return 'text-orange-600 bg-orange-100 dark:bg-orange-900/30';
      case 'medium': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30';
      case 'low': return 'text-green-600 bg-green-100 dark:bg-green-900/30';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ScanSearch className="h-4 w-4" />
            {t('admin.shield.title')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{t('admin.shield.description')}</p>

          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">{t('admin.shield.selectAgent')}</label>
              <select
                className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                disabled={loadingAgents}
              >
                <option value="">{loadingAgents ? t('common.loading') : t('admin.shield.selectAgentPlaceholder')}</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
            <Button onClick={handleScan} disabled={!selectedAgent || scanning}>
              {scanning && <Spinner className="h-4 w-4 mr-2" />}
              <ScanSearch className="h-4 w-4 mr-1" />
              {t('admin.shield.scan')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Scan Results */}
      {scanResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {t('admin.shield.results')}: {scanResult.agent_name}
              <Badge
                className={severityColor(scanResult.risk_level)}
                variant="outline"
              >
                {scanResult.risk_level.toUpperCase()}
              </Badge>
              {scanResult.passed && (
                <Badge variant="outline" className="text-green-600 bg-green-100">
                  {t('admin.shield.passed')}
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{scanResult.total_findings}</div>
                <div className="text-xs text-muted-foreground">{t('admin.shield.findings')}</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{Object.keys(scanResult.summary).length}</div>
                <div className="text-xs text-muted-foreground">{t('admin.shield.categories')}</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className={`text-2xl font-bold ${scanResult.passed ? 'text-green-600' : 'text-red-600'}`}>
                  {scanResult.passed ? '✓' : '✗'}
                </div>
                <div className="text-xs text-muted-foreground">{t('admin.shield.status')}</div>
              </div>
            </div>

            {scanResult.findings.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Shield className="h-10 w-10 mx-auto mb-2" />
                <p>{t('admin.shield.noFindings')}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {scanResult.findings.map((finding, idx) => (
                  <Card key={idx} size="sm">
                    <CardContent className="py-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge className={severityColor(finding.severity)} variant="outline">
                            {finding.severity.toUpperCase()}
                          </Badge>
                          <span className="font-medium text-sm">{finding.description}</span>
                        </div>
                        <Badge variant="secondary" className="text-xs font-mono">
                          {finding.rule_id}
                        </Badge>
                      </div>
                      {finding.evidence && (
                        <div className="text-xs text-muted-foreground bg-muted p-2 rounded font-mono break-all">
                          {finding.evidence}
                        </div>
                      )}
                      {finding.recommendation && (
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                          {finding.recommendation}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}


// ── Main Admin Page ──────────────────────────────────────────────────────────

export default function AdminPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
        <Shield className="h-16 w-16 text-muted-foreground" />
        <h1 className="text-2xl font-bold">{t('admin.accessDenied')}</h1>
        <p className="text-muted-foreground text-center max-w-md">
          {t('admin.accessDeniedDesc')}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('admin.title')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('admin.subtitle')}
        </p>
      </div>

      <Tabs defaultValue="vector" className="w-full">
        <TabsList>
          <TabsTrigger value="vector">
            <Cpu className="h-4 w-4 mr-1.5" />
            {t('admin.tabs.vectorConfig')}
          </TabsTrigger>
          <TabsTrigger value="knowledge">
            <LibraryBig className="h-4 w-4 mr-1.5" />
            {t('admin.tabs.knowledgeBases')}
          </TabsTrigger>
          <TabsTrigger value="users">
            <Users className="h-4 w-4 mr-1.5" />
            {t('admin.tabs.users')}
          </TabsTrigger>
        <TabsTrigger value="shield">
            <ScanSearch className="h-4 w-4 mr-1.5" />
            {t('admin.tabs.shield')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="vector" className="mt-4">
          <VectorConfigTab />
        </TabsContent>

        <TabsContent value="knowledge" className="mt-4">
          <KnowledgeBaseTab />
        </TabsContent>

        <TabsContent value="users" className="mt-4">
          <UsersTab />
        </TabsContent>

        <TabsContent value="shield" className="mt-4">
          <AgentShieldTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}