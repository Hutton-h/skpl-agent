/**
 * Settings Page — 用户设置页面
 *
 * 功能:
 * - 查看当前用户信息 (user_id, username, role)
 * - 配置后端服务器地址
 * - 管理员可跳转到管理面板
 * - 退出登录
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Server,
  Shield,
  LogOut,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { clearAuth } from '@/api/client';

export function SettingsPage() {
  const navigate = useNavigate();
  const userId = localStorage.getItem('user_id') || '未设置';
  const username = localStorage.getItem('username') || '未设置';
  const userRole = localStorage.getItem('user_role') || 'user';
  const isAdmin = userRole === 'admin';

  const [serverUrl, setServerUrl] = useState(() => {
    const stored = localStorage.getItem('server_url');
    return stored || '';
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveServerUrl = () => {
    setIsSaving(true);
    try {
      let normalized = serverUrl.trim();
      if (normalized) {
        if (!/^https?:\/\//i.test(normalized)) {
          normalized = 'http://' + normalized;
        }
        normalized = normalized.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
        normalized = normalized.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');
        try {
          new URL(normalized);
        } catch {
          toast.error('服务器地址格式无效');
          setIsSaving(false);
          return;
        }
      }
      localStorage.setItem('server_url', normalized);
      toast.success('服务器地址已保存');
    } catch {
      toast.error('保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    clearAuth();
    localStorage.removeItem('server_url');
    window.location.href = '/setup';
  };

  return (
    <div className="flex flex-col gap-6 p-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">用户设置</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          管理你的账户信息和连接配置
        </p>
      </div>

      {/* User Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <User className="w-4 h-4" />
            账户信息
          </CardTitle>
          <CardDescription>当前登录用户的基本信息</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">用户名</span>
            <span className="text-sm font-medium">{username}</span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">用户 ID</span>
            <span className="text-sm font-mono text-xs bg-muted px-2 py-0.5 rounded select-all">
              {userId}
            </span>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">角色</span>
            <Badge variant={isAdmin ? 'default' : 'secondary'}>
              {isAdmin ? '管理员' : '普通用户'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Server URL Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Server className="w-4 h-4" />
            后端服务器地址
          </CardTitle>
          <CardDescription>
            配置 SKPL Agent 控制中心的后端地址。修改后立即生效，无需重启。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="server-url">服务器地址</Label>
            <div className="flex gap-2">
              <Input
                id="server-url"
                placeholder="http://localhost:8000"
                value={serverUrl}
                onChange={(e) => setServerUrl(e.target.value)}
              />
              <Button
                onClick={handleSaveServerUrl}
                disabled={isSaving}
                className="gap-2 shrink-0"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                保存
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              留空则使用默认地址 http://localhost:8000
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Admin Panel Link */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="w-4 h-4" />
              管理员功能
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => navigate('/admin')}
            >
              <Shield className="w-4 h-4" />
              进入管理面板
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Logout */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2 text-destructive">
            <LogOut className="w-4 h-4" />
            退出登录
          </CardTitle>
          <CardDescription>
            退出后将返回登录页面，需要重新输入凭据
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            className="gap-2"
            onClick={handleLogout}
          >
            <LogOut className="w-4 h-4" />
            退出登录
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default SettingsPage;