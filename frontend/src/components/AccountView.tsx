import { useCallback, useEffect, useMemo, useState } from 'react';
import { Copy, KeyRound, RefreshCw, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface UserPublic {
  id: string;
  email: string;
  created_at: string;
}

interface ApiKeyListItem {
  id: string;
  name?: string | null;
  prefix: string;
  created_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
}

interface ApiKeyCreateResponse {
  id: string;
  name?: string | null;
  prefix: string;
  api_key: string;
  created_at: string;
}

const apiBase = import.meta.env.VITE_API_BASE ?? '';

async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${apiBase}${path}`, {
    credentials: 'include',
    ...init,
  });
}

const toLocalTime = (iso?: string | null) => {
  if (!iso) return '未使用';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

interface AccountViewProps {
  user: UserPublic;
}

export function AccountView({ user }: AccountViewProps) {
  const [keys, setKeys] = useState<ApiKeyListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createName, setCreateName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreateResponse | null>(null);
  const [ackCopied, setAckCopied] = useState(false);
  const [copyHint, setCopyHint] = useState<string | null>(null);
  const [revokeLoadingId, setRevokeLoadingId] = useState<string | null>(null);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await apiFetch('/api/api-keys');
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `加载失败 (${resp.status})`);
      }
      const data = (await resp.json()) as { items?: ApiKeyListItem[] };
      setKeys(data.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const payload = createName.trim() ? { name: createName.trim() } : {};
      const resp = await apiFetch('/api/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `创建失败 (${resp.status})`);
      }
      const data = (await resp.json()) as ApiKeyCreateResponse;
      setCreatedKey(data);
      setAckCopied(false);
      setCopyHint(null);
      setCreateName('');
      await loadKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    if (!window.confirm('确定撤销该 API Key？撤销后不可恢复。')) {
      return;
    }
    setRevokeLoadingId(keyId);
    setError(null);
    try {
      const resp = await apiFetch(`/api/api-keys/${encodeURIComponent(keyId)}`, { method: 'DELETE' });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `撤销失败 (${resp.status})`);
      }
      await loadKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : '撤销失败');
    } finally {
      setRevokeLoadingId(null);
    }
  };

  const handleCopy = async () => {
    if (!createdKey?.api_key) return;
    try {
      await navigator.clipboard.writeText(createdKey.api_key);
      setCopyHint('已复制');
    } catch {
      setCopyHint('复制失败，请手动复制');
    }
  };

  const userCreatedAt = useMemo(() => toLocalTime(user.created_at), [user.created_at]);

  const closeDialog = () => {
    setCreatedKey(null);
    setAckCopied(false);
    setCopyHint(null);
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <div className="border border-gray-200 rounded-2xl p-5 bg-white">
          <div className="text-sm font-semibold text-gray-900">基础信息</div>
          <div className="mt-4 space-y-3 text-sm text-gray-600">
            <div>
              <div className="text-xs text-gray-400">邮箱</div>
              <div className="text-sm text-gray-900">{user.email}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">注册时间</div>
              <div className="text-sm text-gray-900">{userCreatedAt}</div>
            </div>
          </div>
          <div className="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-500">
            API Key 用于通过接口访问数据与智能体能力，创建后仅显示一次，请妥善保存。
          </div>
        </div>

        <div className="border border-gray-200 rounded-2xl p-5 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-gray-900">API Keys</div>
              <div className="text-xs text-gray-400 mt-1">用于接口调用的访问凭证</div>
            </div>
            <Button type="button" variant="outline" onClick={() => void loadKeys()} disabled={loading}>
              <RefreshCw className="w-4 h-4" />
              刷新
            </Button>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <input
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              placeholder="Key 名称（可选）"
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-gray-300 flex-1 min-w-[200px]"
              maxLength={64}
            />
            <Button type="button" onClick={() => void handleCreate()} disabled={creating}>
              <KeyRound className="w-4 h-4" />
              创建 API Key
            </Button>
          </div>

          {error && <div className="mt-3 text-xs text-red-500">{error}</div>}

          <div className="mt-5 border-t border-gray-100 pt-4">
            {loading ? (
              <div className="text-sm text-gray-500">加载中…</div>
            ) : keys.length === 0 ? (
              <div className="text-sm text-gray-500">暂无 API Key</div>
            ) : (
              <div className="space-y-3">
                {keys.map((item) => {
                  const revoked = Boolean(item.revoked_at);
                  return (
                    <div key={item.id} className="border border-gray-100 rounded-xl p-3">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium text-gray-900">
                          {(item.name && item.name.trim()) || '未命名'}
                        </div>
                        {revoked ? (
                          <Badge variant="secondary" className="text-[10px] bg-gray-100 text-gray-500 border-0">
                            已撤销
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px] bg-emerald-50 text-emerald-600 border-0">
                            可用
                          </Badge>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        前缀：<span className="font-mono text-gray-700">{item.prefix}</span>
                      </div>
                      <div className="mt-1 text-[11px] text-gray-400 flex flex-wrap gap-3">
                        <span>创建：{toLocalTime(item.created_at)}</span>
                        <span>最后使用：{toLocalTime(item.last_used_at)}</span>
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <div className="text-[11px] text-gray-400">
                          {revoked ? `撤销于 ${toLocalTime(item.revoked_at)}` : '可用于 API 请求'}
                        </div>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          disabled={revoked || revokeLoadingId === item.id}
                          onClick={() => void handleRevoke(item.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                          撤销
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <Dialog
        open={Boolean(createdKey)}
        onOpenChange={(nextOpen) => {
          if (!nextOpen && !ackCopied) {
            return;
          }
          if (!nextOpen) {
            closeDialog();
          }
        }}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>API Key 创建成功</DialogTitle>
            <DialogDescription>该 Key 仅显示一次，请立即复制并妥善保存。</DialogDescription>
          </DialogHeader>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs font-mono break-all">
            {createdKey?.api_key}
          </div>
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{copyHint ?? '点击复制后请确认已保存'}</span>
            <button
              type="button"
              onClick={() => void handleCopy()}
              className="inline-flex items-center gap-1 text-gray-700 hover:text-gray-900"
            >
              <Copy className="w-3 h-3" />
              复制
            </button>
          </div>

          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input type="checkbox" checked={ackCopied} onChange={(e) => setAckCopied(e.target.checked)} />
            我已复制并安全保存
          </label>

          <DialogFooter>
            <Button type="button" onClick={closeDialog} disabled={!ackCopied}>
              完成
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
