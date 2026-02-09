import { useMemo } from 'react';

interface JsonPreviewProps {
  value: unknown;
  maxHeight?: number;
}

export function JsonPreview({ value, maxHeight = 240 }: JsonPreviewProps) {
  const text = useMemo(() => {
    if (value === undefined) {
      return '';
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }, [value]);

  if (!text) {
    return <div className="text-xs text-gray-400">暂无数据</div>;
  }

  return (
    <pre
      className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto"
      style={{ maxHeight }}
    >
      {text}
    </pre>
  );
}

