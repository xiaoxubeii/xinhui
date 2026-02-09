import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Download, Paperclip, Search, Trash2, Upload } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type ArtifactCategory =
  | 'cpet_report'
  | 'exercise_data'
  | 'health_data'
  | 'diet_data'
  | 'lab_report'
  | 'imaging_report'
  | 'other';

interface ArtifactListItem {
  id: string;
  category: ArtifactCategory;
  title?: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  has_extracted_text: boolean;
  has_parsed_json: boolean;
}

interface ArtifactDetailResponse {
  id: string;
  category: ArtifactCategory;
  title?: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  extracted_text?: string | null;
  parsed_json?: unknown;
}

const apiBase = import.meta.env.VITE_API_BASE ?? '';

async function apiFetch(path: string, init?: RequestInit) {
  return fetch(`${apiBase}${path}`, {
    credentials: 'include',
    ...init,
  });
}

const CATEGORY_TABS: Array<{ id: 'all' | ArtifactCategory; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'cpet_report', label: 'CPET' },
  { id: 'exercise_data', label: '运动' },
  { id: 'health_data', label: '健康' },
  { id: 'diet_data', label: '营养' },
  { id: 'lab_report', label: '化验' },
  { id: 'imaging_report', label: '影像' },
  { id: 'other', label: '其他' },
];

const CATEGORY_LABEL: Record<ArtifactCategory, string> = {
  cpet_report: 'CPET',
  exercise_data: '运动',
  health_data: '健康',
  diet_data: '营养',
  lab_report: '化验',
  imaging_report: '影像',
  other: '其他',
};

const formatBytes = (bytes: number) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let n = bytes;
  let idx = 0;
  while (n >= 1024 && idx < units.length - 1) {
    n /= 1024;
    idx += 1;
  }
  const fixed = idx === 0 ? 0 : n >= 10 ? 1 : 2;
  return `${n.toFixed(fixed)} ${units[idx]}`;
};

const toLocalDateTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

const isPdf = (item?: { filename?: string; content_type?: string } | null) => {
  if (!item) return false;
  const ct = (item.content_type || '').toLowerCase();
  if (ct.includes('pdf')) return true;
  return (item.filename || '').toLowerCase().endsWith('.pdf');
};

const isImage = (item?: { filename?: string; content_type?: string } | null) => {
  if (!item) return false;
  const ct = (item.content_type || '').toLowerCase();
  if (ct.startsWith('image/')) return true;
  const name = (item.filename || '').toLowerCase();
  return ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'].some((ext) => name.endsWith(ext));
};

interface ArtifactsLibraryViewProps {
  activeSessionId: string | null;
  attachedArtifactIds: Set<string>;
  onAttachmentsChanged?: () => void;
  defaultCategory?: ArtifactCategory;
}

export function ArtifactsLibraryView({
  activeSessionId,
  attachedArtifactIds,
  onAttachmentsChanged,
  defaultCategory = 'other',
}: ArtifactsLibraryViewProps) {
  const [category, setCategory] = useState<'all' | ArtifactCategory>('all');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [items, setItems] = useState<ArtifactListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ArtifactDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [attachLoading, setAttachLoading] = useState(false);
  const [actionHint, setActionHint] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadCategory, setUploadCategory] = useState<ArtifactCategory>(defaultCategory);
  const [attachOnUpload, setAttachOnUpload] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('limit', '200');
      params.set('offset', '0');
      if (category !== 'all') params.set('category', category);
      if (debouncedQuery) params.set('q', debouncedQuery);
      const resp = await apiFetch(`/api/artifacts?${params.toString()}`);
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `加载失败 (${resp.status})`);
      }
      const data = (await resp.json()) as { items?: ArtifactListItem[] };
      const next = data.items ?? [];
      setItems(next);

      // Keep selection stable when possible.
      setSelectedId((prev) => {
        if (prev && next.some((it) => it.id === prev)) return prev;
        return next.length > 0 ? next[0].id : null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
      setItems([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  }, [category, debouncedQuery]);

  useEffect(() => {
    void fetchList();
  }, [fetchList]);

  const fetchDetail = useCallback(async (artifactId: string) => {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const resp = await apiFetch(`/api/artifacts/${encodeURIComponent(artifactId)}`);
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `加载失败 (${resp.status})`);
      }
      const data = (await resp.json()) as ArtifactDetailResponse;
      setDetail(data);
    } catch (err) {
      setDetail(null);
      setDetailError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void fetchDetail(selectedId);
  }, [fetchDetail, selectedId]);

  // Cleanup object URLs to avoid memory leaks.
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // For PDFs/images, fetch as blob and render via object URL (download endpoint returns attachment).
  useEffect(() => {
    if (!detail || (!isPdf(detail) && !isImage(detail))) {
      setPreviewUrl(null);
      setPreviewError(null);
      setPreviewLoading(false);
      return;
    }

    let cancelled = false;
    setPreviewUrl(null);
    setPreviewLoading(true);
    setPreviewError(null);

    (async () => {
      try {
        const resp = await apiFetch(`/api/artifacts/${encodeURIComponent(detail.id)}/download`);
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `预览加载失败 (${resp.status})`);
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        setPreviewUrl(url);
      } catch (err) {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : '预览加载失败');
        }
      } finally {
        if (!cancelled) {
          setPreviewLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [detail]);

  const selectedListItem = useMemo(
    () => items.find((it) => it.id === selectedId) ?? null,
    [items, selectedId]
  );

  const selectedAttached = useMemo(() => {
    if (!selectedId) return false;
    return attachedArtifactIds.has(selectedId);
  }, [attachedArtifactIds, selectedId]);

  const handleAttachToggle = async () => {
    if (!selectedId) return;
    if (!activeSessionId) {
      setActionHint('请先选择一个会话后再附加');
      return;
    }
    setAttachLoading(true);
    setActionHint(null);
    try {
      const method = selectedAttached ? 'DELETE' : 'POST';
      const resp = await apiFetch(
        `/api/chat/sessions/${encodeURIComponent(activeSessionId)}/artifacts/${encodeURIComponent(selectedId)}`,
        { method }
      );
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `操作失败 (${resp.status})`);
      }
      setActionHint(selectedAttached ? '已从会话移除' : '已附加到会话');
      onAttachmentsChanged?.();
    } catch (err) {
      setActionHint(err instanceof Error ? err.message : '操作失败');
    } finally {
      setAttachLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    if (!window.confirm('确定删除该文件？删除后不可恢复。')) return;
    setActionHint(null);
    try {
      const resp = await apiFetch(`/api/artifacts/${encodeURIComponent(selectedId)}`, { method: 'DELETE' });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `删除失败 (${resp.status})`);
      }
      setDetail(null);
      setSelectedId(null);
      onAttachmentsChanged?.();
      await fetchList();
    } catch (err) {
      setActionHint(err instanceof Error ? err.message : '删除失败');
    }
  };

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setActionHint(null);
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append('category', uploadCategory);
        if (attachOnUpload && activeSessionId) {
          form.append('attach_session_id', activeSessionId);
        }
        form.append('file', file);
        const resp = await apiFetch('/api/artifacts/upload', { method: 'POST', body: form });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `上传失败 (${resp.status})`);
        }
      }
      setActionHint('上传成功');
      await fetchList();
      if (attachOnUpload && activeSessionId) {
        onAttachmentsChanged?.();
      }
    } catch (err) {
      setActionHint(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const downloadUrl = selectedId ? `${apiBase}/api/artifacts/${encodeURIComponent(selectedId)}/download` : null;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: list */}
      <div className="w-[380px] border-r border-gray-100 flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between gap-3">
            <Tabs value={category} onValueChange={(v) => setCategory(v as 'all' | ArtifactCategory)}>
              <TabsList className="flex-wrap h-auto">
                {CATEGORY_TABS.map((t) => (
                  <TabsTrigger key={t.id} value={t.id} className="text-xs">
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-gray-400 absolute left-2 top-2.5" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索文件名/标题…"
                className="w-full border border-gray-200 rounded-lg pl-8 pr-3 py-2 text-sm outline-none focus:border-gray-300"
              />
            </div>
            <Button
              type="button"
              variant="outline"
              className="h-9 px-3"
              onClick={() => void fetchList()}
              disabled={loading}
            >
              刷新
            </Button>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <select
              value={uploadCategory}
              onChange={(e) => setUploadCategory(e.target.value as ArtifactCategory)}
              className="border border-gray-200 rounded-lg px-2 py-2 text-sm bg-white outline-none focus:border-gray-300"
              title="上传分类"
            >
              {CATEGORY_TABS.filter((t) => t.id !== 'all').map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-xs text-gray-600 select-none">
              <input
                type="checkbox"
                checked={attachOnUpload}
                onChange={(e) => setAttachOnUpload(e.target.checked)}
                disabled={!activeSessionId}
              />
              上传后附加到当前会话
            </label>
            <Button
              type="button"
              variant="outline"
              className="h-9 px-3 ml-auto"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <Upload className="w-4 h-4" />
              上传
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".csv,.json,.txt,.pdf,.png,.jpg,.jpeg,.webp,application/pdf,text/csv,application/json,text/plain,image/*"
              multiple
              onChange={(event) => {
                void handleUploadFiles(event.target.files);
                event.currentTarget.value = '';
              }}
            />
          </div>

          {actionHint && <div className="mt-2 text-xs text-gray-500">{actionHint}</div>}
          {error && <div className="mt-2 text-xs text-red-500">{error}</div>}
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-sm text-gray-500">加载中…</div>
          ) : items.length === 0 ? (
            <div className="p-4 text-sm text-gray-500">暂无文件</div>
          ) : (
            <div className="p-2 space-y-1">
              {items.map((it) => {
                const active = it.id === selectedId;
                const attached = attachedArtifactIds.has(it.id);
                return (
                  <button
                    key={it.id}
                    type="button"
                    onClick={() => setSelectedId(it.id)}
                    className={`w-full text-left rounded-xl px-3 py-2 border transition-colors ${
                      active ? 'border-gray-300 bg-gray-50' : 'border-transparent hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-gray-900 flex-1 truncate">
                        {(it.title && it.title.trim()) || it.filename}
                      </div>
                      {attached && (
                        <Badge variant="secondary" className="text-[10px] bg-emerald-50 text-emerald-600 border-0">
                          已附加
                        </Badge>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-gray-500">
                      <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                        {CATEGORY_LABEL[it.category] ?? it.category}
                      </span>
                      {it.has_parsed_json ? (
                        <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">已解析</span>
                      ) : it.has_extracted_text ? (
                        <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">可预览</span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">原文件</span>
                      )}
                      <span>{formatBytes(it.size_bytes)}</span>
                      <span className="ml-auto">{toLocalDateTime(it.created_at)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right: preview */}
      <div className="flex-1 overflow-y-auto">
        {!selectedId ? (
          <div className="p-8 text-sm text-gray-500">选择左侧文件查看详情</div>
        ) : detailLoading ? (
          <div className="p-8 text-sm text-gray-500">加载详情…</div>
        ) : detailError ? (
          <div className="p-8 text-sm text-red-500">{detailError}</div>
        ) : !detail ? (
          <div className="p-8 text-sm text-gray-500">暂无详情</div>
        ) : (
          <div className="p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-base font-semibold text-gray-900">
                  {(detail.title && detail.title.trim()) || detail.filename}
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {CATEGORY_LABEL[detail.category] ?? detail.category} · {formatBytes(detail.size_bytes)} ·{' '}
                  {toLocalDateTime(detail.created_at)}
                </div>
                <div className="mt-1 text-[11px] text-gray-400 break-all">SHA256: {detail.sha256}</div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant={selectedAttached ? 'secondary' : 'default'}
                  onClick={() => void handleAttachToggle()}
                  disabled={attachLoading}
                  title={activeSessionId ? '附加/移除到当前会话' : '请先选择会话'}
                >
                  <Paperclip className="w-4 h-4" />
                  {selectedAttached ? '从会话移除' : '附加到会话'}
                </Button>
                <Button type="button" variant="outline" asChild disabled={!downloadUrl}>
                  <a href={downloadUrl ?? '#'} target="_blank" rel="noreferrer">
                    <Download className="w-4 h-4" />
                    下载
                  </a>
                </Button>
                <Button type="button" variant="destructive" onClick={() => void handleDelete()} disabled={!selectedId}>
                  <Trash2 className="w-4 h-4" />
                  删除
                </Button>
              </div>
            </div>

            <div className="mt-6 border border-gray-200 rounded-2xl overflow-hidden">
              {isPdf(detail) ? (
                previewLoading ? (
                  <div className="p-6 text-sm text-gray-500 bg-white">加载预览…</div>
                ) : previewError ? (
                  <div className="p-6 text-sm text-red-500 bg-white">{previewError}</div>
                ) : (
                  <iframe title="pdf-preview" src={previewUrl ?? ''} className="w-full h-[70vh] bg-white" />
                )
              ) : isImage(detail) ? (
                previewLoading ? (
                  <div className="p-6 text-sm text-gray-500 bg-white">加载预览…</div>
                ) : previewError ? (
                  <div className="p-6 text-sm text-red-500 bg-white">{previewError}</div>
                ) : (
                  <div className="p-4 bg-white flex justify-center">
                    <img src={previewUrl ?? ''} alt={detail.filename} className="max-w-full max-h-[70vh] rounded-lg" />
                  </div>
                )
              ) : detail.parsed_json ? (
                <pre className="p-4 text-xs overflow-auto bg-white">
                  {JSON.stringify(detail.parsed_json, null, 2)}
                </pre>
              ) : detail.extracted_text ? (
                <pre className="p-4 text-xs overflow-auto bg-white whitespace-pre-wrap">
                  {detail.extracted_text}
                </pre>
              ) : (
                <div className="p-6 text-sm text-gray-500 bg-white">
                  暂无可预览内容，请下载原文件查看。
                </div>
              )}
            </div>

            {selectedListItem && !isPdf(selectedListItem) && !isImage(selectedListItem) && !detail.extracted_text && (
              <div className="mt-3 text-xs text-gray-500">提示：此类型文件可能无法在浏览器内直接预览。</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
