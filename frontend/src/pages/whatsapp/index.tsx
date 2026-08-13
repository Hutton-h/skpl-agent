/**
 * WhatsApp Configuration Page
 * 
 * 使用 credential 系统存储 WhatsApp Cloud API 凭据，
 * 通过 notification API 测试发送，与对话界面的 SendNotification 工具集成。
 */
import { useState, useEffect, useCallback } from 'react';
import {
  MessageCircle,
  Check,
  ExternalLink,
  Loader2,
  Eye,
  EyeOff,
  Send,
  Smartphone,
  Key,
  Globe,
  AlertCircle,
  BadgeCheck,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { credentialApi } from '@/api/credential';
import { client } from '@/api/client';
import type { CredentialView } from '@/api/types';

type Step = 1 | 2 | 3 | 4;

export default function WhatsAppPage() {
  const [step, setStep] = useState<Step>(1);
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [defaultRecipient, setDefaultRecipient] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success?: boolean; message?: string }>({});
  const [isSaving, setIsSaving] = useState(false);

  // Existing credential state
  const [existingCredential, setExistingCredential] = useState<CredentialView | null>(null);
  const [isLoadingCred, setIsLoadingCred] = useState(true);
  const [hasChannel, setHasChannel] = useState(false);

  // Load existing WhatsApp credential on mount
  const loadExisting = useCallback(async () => {
    setIsLoadingCred(true);
    try {
      const list = await credentialApi.list();
      const wa = list.credentials.find(
        (c) => (c.data as Record<string, unknown>)?.type === 'whatsapp_credential'
      );
      if (wa) {
        setExistingCredential(wa);
        const data = wa.data as Record<string, unknown>;
        setPhoneNumberId((data.phone_number_id as string) || '');
        setAccessToken((data.access_token as string) || '');
        setDefaultRecipient((data.default_recipient as string) || '');
        setStep(4); // Jump to config step
      }

      // Check notification channels
      try {
        const channelsRes = await client.get<{ whatsapp: boolean; email: boolean }>('/notification/channels');
        setHasChannel(channelsRes.whatsapp);
      } catch {
        // Ignore - channels endpoint may not be available
      }
    } catch {
      // Ignore - may not have credentials yet
    } finally {
      setIsLoadingCred(false);
    }
  }, []);

  useEffect(() => {
    loadExisting();
  }, [loadExisting]);

  const handleSave = async () => {
    if (!phoneNumberId || !accessToken) {
      toast.error('请填写 Phone Number ID 和 Access Token');
      return;
    }
    setIsSaving(true);
    try {
      const credentialData = {
        type: 'whatsapp_credential',
        phone_number_id: phoneNumberId,
        access_token: accessToken,
        default_recipient: defaultRecipient,
        api_version: 'v21.0',
      };

      if (existingCredential) {
        // Update existing credential
        await credentialApi.update(existingCredential.id, { data: credentialData });
        toast.success('WhatsApp 配置已更新');
      } else {
        // Create new credential
        await credentialApi.create({ data: credentialData });
        toast.success('WhatsApp 配置已保存');
      }

      // Reload to get updated state
      await loadExisting();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '保存失败';
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    if (!phoneNumberId || !accessToken) {
      toast.error('请先填写并保存配置');
      return;
    }
    if (!defaultRecipient) {
      toast.error('请填写默认接收号码');
      return;
    }
    setIsTesting(true);
    setTestResult({});
    try {
      const res = await client.post<{ ok: boolean; detail: string }>('/notification/test', {
        channel: 'whatsapp',
        recipient: defaultRecipient,
        message: 'SKPL Agent 测试通知 - 这是一条来自 AI 助手的测试消息',
      });
      if (res.ok) {
        setTestResult({ success: true, message: '测试消息发送成功！请检查你的 WhatsApp' });
      } else {
        setTestResult({ success: false, message: res.detail || '发送失败，请检查配置' });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '测试失败，请检查网络连接';
      setTestResult({ success: false, message: msg });
    } finally {
      setIsTesting(false);
    }
  };

  const steps = [
    {
      num: 1,
      title: '注册 Meta 开发者',
      desc: '访问 Meta for Developers 创建开发者账号',
      action: 'https://developers.facebook.com/',
      actionLabel: '前往注册',
    },
    {
      num: 2,
      title: '创建 WhatsApp 应用',
      desc: '在 Meta 应用面板创建新应用并启用 WhatsApp 产品',
      action: 'https://developers.facebook.com/apps/',
      actionLabel: '创建应用',
    },
    {
      num: 3,
      title: '获取配置密钥',
      desc: '在 WhatsApp 设置中找到 Phone Number ID 和 Access Token',
      action: 'https://business.facebook.com/wa/manage/',
      actionLabel: 'WhatsApp 管理',
    },
    {
      num: 4,
      title: '填写并保存',
      desc: '将获取到的密钥填入下方表单，保存并测试',
    },
  ];

  if (isLoadingCred) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-r from-green-400 to-green-600 flex items-center justify-center">
          <MessageCircle className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">WhatsApp 通知配置</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            配置 WhatsApp Cloud API，让 AI 通过 WhatsApp 给你发送通知消息
          </p>
        </div>
      </div>

      {/* Status banner */}
      {existingCredential && (
        <Card className="border-green-200 bg-green-50/50">
          <CardContent className="py-4 flex items-center gap-3">
            <BadgeCheck className="w-5 h-5 text-green-600" />
            <div>
              <p className="font-medium text-green-800">WhatsApp 已配置</p>
              <p className="text-sm text-green-600">
                在对话界面中，AI 可以使用 SendNotification 工具通过 WhatsApp 向你发送消息。
                你可以在聊天面板的"通知"标签页中管理通知事件和渠道。
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step Indicator */}
      <div className="flex items-center gap-2">
        {steps.map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <button
              onClick={() => setStep(s.num as Step)}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                s.num < step
                  ? 'bg-green-100 text-green-600'
                  : s.num === step
                  ? 'bg-gradient-to-r from-green-400 to-green-600 text-white shadow-md scale-110'
                  : 'bg-gray-100 text-gray-400'
              }`}
            >
              {s.num < step ? <Check className="w-4 h-4" /> : s.num}
            </button>
            {s.num < 4 && <div className="w-8 h-0.5 bg-gray-200" />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            第 {step} 步：{steps[step - 1].title}
          </CardTitle>
          <CardDescription>{steps[step - 1].desc}</CardDescription>
        </CardHeader>
        <CardContent>
          {step === 1 && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  <strong>需要准备：</strong>一个 Facebook 账号（个人或企业均可），无需企业认证。
                </p>
              </div>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                <li>打开 Meta for Developers 网站</li>
                <li>使用你的 Facebook 账号登录</li>
                <li>完成开发者注册（免费，约 1 分钟）</li>
                <li>点击"创建应用"进入下一步</li>
              </ol>
              <a href={steps[0].action} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="gap-2">
                  <ExternalLink className="w-4 h-4" />
                  {steps[0].actionLabel}
                </Button>
              </a>
              <div className="flex justify-end">
                <Button onClick={() => setStep(2)}>下一步</Button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-4">
                <p className="text-sm text-amber-800">
                  <strong>注意：</strong>选择"Business"类型应用，然后找到 WhatsApp 产品并点击"Set up"。
                </p>
              </div>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                <li>在应用面板点击"创建应用"</li>
                <li>选择"Business"类型</li>
                <li>填写应用名称（如"SKPL Notifier"）</li>
                <li>创建完成后，在左侧菜单找到"WhatsApp"</li>
                <li>点击"Set up"激活 WhatsApp 功能</li>
              </ol>
              <a href={steps[1].action} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="gap-2">
                  <ExternalLink className="w-4 h-4" />
                  {steps[1].actionLabel}
                </Button>
              </a>
              <div className="flex justify-between">
                <Button variant="ghost" onClick={() => setStep(1)}>上一步</Button>
                <Button onClick={() => setStep(3)}>下一步</Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-purple-50 border border-purple-100 rounded-lg p-4">
                <p className="text-sm text-purple-800">
                  <strong>需要两个密钥：</strong>Phone Number ID（测试号码的 ID）和 Access Token（临时或永久访问令牌）。
                </p>
              </div>
              <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                <li>在 WhatsApp 管理页面，找到"API Setup"</li>
                <li>复制 <strong>Phone Number ID</strong>（一串数字）</li>
                <li>在"Access Token"区域点击"Generate"</li>
                <li>复制 <strong>Access Token</strong>（长字符串）</li>
                <li>将测试号码添加到你的 WhatsApp 联系人</li>
              </ol>
              <a href={steps[2].action} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="gap-2">
                  <ExternalLink className="w-4 h-4" />
                  {steps[2].actionLabel}
                </Button>
              </a>
              <div className="flex justify-between">
                <Button variant="ghost" onClick={() => setStep(2)}>上一步</Button>
                <Button onClick={() => setStep(4)}>下一步：填写配置</Button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="phone-number-id">
                    <Smartphone className="w-3.5 h-3.5 inline mr-1" />
                    Phone Number ID
                  </Label>
                  <Input
                    id="phone-number-id"
                    placeholder="例如：123456789012345"
                    value={phoneNumberId}
                    onChange={(e) => setPhoneNumberId(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="access-token">
                    <Key className="w-3.5 h-3.5 inline mr-1" />
                    Access Token
                  </Label>
                  <div className="relative">
                    <Input
                      id="access-token"
                      type={showToken ? 'text' : 'password'}
                      placeholder="EAAxxxxxxxxxxxx..."
                      value={accessToken}
                      onChange={(e) => setAccessToken(e.target.value)}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowToken(!showToken)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="recipient">
                    <Globe className="w-3.5 h-3.5 inline mr-1" />
                    默认接收号码（可选）
                  </Label>
                  <Input
                    id="recipient"
                    placeholder="例如：+8613800138000"
                    value={defaultRecipient}
                    onChange={(e) => setDefaultRecipient(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    填写你的 WhatsApp 号码（含国家区号），用于接收通知
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={isSaving} className="gap-2">
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {existingCredential ? '更新配置' : '保存配置'}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={isTesting || !phoneNumberId || !accessToken}
                  className="gap-2"
                >
                  {isTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  发送测试消息
                </Button>
              </div>

              {testResult.message && (
                <div
                  className={`p-3 rounded-lg text-sm flex items-start gap-2 ${
                    testResult.success
                      ? 'bg-green-50 text-green-800 border border-green-100'
                      : 'bg-red-50 text-red-800 border border-red-100'
                  }`}
                >
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  {testResult.message}
                </div>
              )}

              <div className="flex justify-start">
                <Button variant="ghost" onClick={() => setStep(3)}>上一步</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* How it works with chat */}
      <Card className="bg-gray-50/50">
        <CardHeader>
          <CardTitle className="text-base">与对话界面集成</CardTitle>
          <CardDescription>
            WhatsApp 配置完成后，AI 助手可以在对话中通过 SendNotification 工具直接发送 WhatsApp 消息
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-start gap-2">
            <span className="text-green-600 font-bold mt-0.5">1</span>
            <div>
              <p className="font-medium">在对话中请求 AI 发送通知</p>
              <p className="text-muted-foreground">
                例如："帮我把这个分析结果发到我的 WhatsApp"
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-green-600 font-bold mt-0.5">2</span>
            <div>
              <p className="font-medium">AI 自动调用 SendNotification 工具</p>
              <p className="text-muted-foreground">
                AI 助手会使用你配置的 WhatsApp 凭据，通过 WhatsApp Cloud API 发送消息
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-green-600 font-bold mt-0.5">3</span>
            <div>
              <p className="font-medium">在聊天面板管理通知</p>
              <p className="text-muted-foreground">
                打开聊天面板的"通知"标签页，可以配置哪些事件触发 WhatsApp 通知（任务完成、错误告警等）
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FAQ */}
      <Card className="bg-gray-50/50">
        <CardHeader>
          <CardTitle className="text-base">常见问题</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <p className="font-medium">测试号码收不到消息？</p>
            <p className="text-muted-foreground">
              需要在 WhatsApp 中将测试号码添加为联系人，然后发送任意消息给该号码激活会话。
            </p>
          </div>
          <div>
            <p className="font-medium">Token 过期了怎么办？</p>
            <p className="text-muted-foreground">
              测试 Token 有效期 24 小时。如需长期使用，请在 Meta 应用中生成永久 Token。
            </p>
          </div>
          <div>
            <p className="font-medium">免费额度是多少？</p>
            <p className="text-muted-foreground">
              Meta 提供 1000 条/月的免费消息额度（测试号码），足以满足个人使用。
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}