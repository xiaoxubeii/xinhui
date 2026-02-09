import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ScopeBarProps {
  title: string;
  subtitle?: string;
  patientId: string;
  onPatientIdChange: (value: string) => void;
  start: string;
  end: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  device: string;
  deviceOptions: string[];
  onDeviceChange: (value: string) => void;
  merge: 'sum' | 'max';
  onMergeChange: (value: 'sum' | 'max') => void;
  onRefresh?: () => void;
  isLoading?: boolean;
  error?: string | null;
}

export function ScopeBar({
  title,
  subtitle,
  patientId,
  onPatientIdChange,
  start,
  end,
  onStartChange,
  onEndChange,
  device,
  deviceOptions,
  onDeviceChange,
  merge,
  onMergeChange,
  onRefresh,
  isLoading,
  error,
}: ScopeBarProps) {
  const mergedDeviceOptions = useMemo(() => {
    const options = deviceOptions.filter(Boolean);
    return options.length > 0 ? options : [];
  }, [deviceOptions]);

  return (
    <div className="border-b border-gray-200 bg-white sticky top-0 z-10">
      <div className="px-6 py-4 flex items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="text-lg font-semibold text-gray-900">{title}</div>
          {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
          {error && <div className="text-xs text-red-600 mt-2">{error}</div>}
        </div>

        <div className="flex flex-wrap items-end justify-end gap-3">
          <div className="w-[220px]">
            <div className="text-[11px] text-gray-500 mb-1">Patient ID</div>
            <Input
              value={patientId}
              onChange={(e) => onPatientIdChange(e.target.value)}
              placeholder="例如：P0001"
            />
          </div>
          <div className="w-[148px]">
            <div className="text-[11px] text-gray-500 mb-1">开始</div>
            <Input type="date" value={start} onChange={(e) => onStartChange(e.target.value)} />
          </div>
          <div className="w-[148px]">
            <div className="text-[11px] text-gray-500 mb-1">结束</div>
            <Input type="date" value={end} onChange={(e) => onEndChange(e.target.value)} />
          </div>
          <div className="w-[200px]">
            <div className="text-[11px] text-gray-500 mb-1">设备</div>
            <Select value={device} onValueChange={onDeviceChange}>
              <SelectTrigger>
                <SelectValue placeholder="all" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部设备</SelectItem>
                {mergedDeviceOptions.map((id) => (
                  <SelectItem key={id} value={id}>
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-[140px]">
            <div className="text-[11px] text-gray-500 mb-1">合并</div>
            <Select value={merge} onValueChange={(v) => onMergeChange(v as 'sum' | 'max')}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sum">求和</SelectItem>
                <SelectItem value="max">取最大</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {onRefresh && (
            <Button variant="secondary" onClick={onRefresh} disabled={isLoading}>
              {isLoading ? '刷新中…' : '刷新'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

