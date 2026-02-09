import { useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import type { ClinicalContextResponse, ClinicalRecordsResponse, ClinicalSubjectsResponse } from '@/lib/apiTypes';
import { JsonPreview } from '@/components/domains/JsonPreview';

interface ClinicalDomainProps {
  patientId: string;
  context: ClinicalContextResponse | null;
  subjects: ClinicalSubjectsResponse | null;
  records: ClinicalRecordsResponse | null;
  isLoading?: boolean;
  onSelectPatientId?: (patientId: string) => void;
}

const formatScalar = (value: unknown) => {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export function ClinicalDomain({
  patientId,
  context,
  subjects,
  records,
  isLoading,
  onSelectPatientId,
}: ClinicalDomainProps) {
  const patient = context?.patient;
  const linkedDeviceIds = context?.linked_device_ids ?? patient?.linked_device_ids ?? [];

  const latestCpetSummary = useMemo(() => {
    if (!context?.latest_cpet) {
      return null;
    }
    const data = context.latest_cpet.data ?? {};
    // Heuristic pick for CPET-like fields.
    const vo2Peak = data['vo2_peak'] ?? data['VO2peak'];
    const hrMax = data['hr_max'] ?? data['HRmax'];
    const maxMets = data['max_mets'] ?? data['METS'];
    return { vo2Peak, hrMax, maxMets };
  }, [context?.latest_cpet]);

  return (
    <div className="px-6 py-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>患者信息</CardTitle>
            <CardDescription>Patient ID: {patientId || '—'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex flex-wrap gap-4">
              <div>
                <div className="text-xs text-gray-500">姓名</div>
                <div className="text-sm text-gray-900">{patient?.name ?? '—'}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">性别</div>
                <div className="text-sm text-gray-900">{patient?.sex ?? 'unknown'}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">年龄</div>
                <div className="text-sm text-gray-900">{patient?.age ?? '—'}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">诊断</div>
              <div className="text-sm text-gray-900">
                {(patient?.diagnosis ?? []).length > 0 ? (patient?.diagnosis ?? []).join('、') : '—'}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">绑定设备</div>
              <div className="text-sm text-gray-900">
                {linkedDeviceIds.length > 0 ? linkedDeviceIds.join(', ') : '—'}
              </div>
            </div>
            {patient?.notes && (
              <div>
                <div className="text-xs text-gray-500">备注</div>
                <div className="text-sm text-gray-900 whitespace-pre-wrap">{patient.notes}</div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>最新 CPET 记录</CardTitle>
            <CardDescription>
              {context?.latest_cpet ? context.latest_cpet.recorded_at : '暂无 CPET 记录'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {context?.latest_cpet ? (
              <>
                {latestCpetSummary && (
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="rounded-lg border border-gray-200 p-3 bg-white">
                      <div className="text-xs text-gray-500">VO2peak</div>
                      <div className="text-base font-semibold text-gray-900">
                        {formatScalar(latestCpetSummary.vo2Peak)}
                      </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 p-3 bg-white">
                      <div className="text-xs text-gray-500">HR max</div>
                      <div className="text-base font-semibold text-gray-900">
                        {formatScalar(latestCpetSummary.hrMax)}
                      </div>
                    </div>
                    <div className="rounded-lg border border-gray-200 p-3 bg-white">
                      <div className="text-xs text-gray-500">Max METS</div>
                      <div className="text-base font-semibold text-gray-900">
                        {formatScalar(latestCpetSummary.maxMets)}
                      </div>
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-xs text-gray-500 mb-2">结构化数据</div>
                  <JsonPreview value={context.latest_cpet.data} maxHeight={220} />
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-500">可在下方“临床记录”中添加 CPET 报告（record_type=cpet_report）。</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>临床记录</CardTitle>
          <CardDescription>按 recorded_at 倒序（最多展示 50 条）</CardDescription>
        </CardHeader>
        <CardContent>
          {records?.records?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Recorded At</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.records.slice(0, 50).map((r) => (
                  <TableRow key={r.record_id}>
                    <TableCell>{r.recorded_at}</TableCell>
                    <TableCell>{r.record_type}</TableCell>
                    <TableCell className="max-w-[320px] truncate" title={r.title ?? ''}>
                      {r.title ?? '—'}
                    </TableCell>
                    <TableCell>{r.source}</TableCell>
                    <TableCell className="font-mono text-xs">{r.record_id}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : isLoading ? (
            <div className="text-sm text-gray-500">加载中…</div>
          ) : (
            <div className="text-sm text-gray-500">暂无记录</div>
          )}
        </CardContent>
      </Card>

      {subjects && subjects.subjects.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>患者列表</CardTitle>
            <CardDescription>点击可切换 Patient ID</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Patient ID</TableHead>
                  <TableHead>姓名</TableHead>
                  <TableHead>性别</TableHead>
                  <TableHead>年龄</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {subjects.subjects.slice(0, 50).map((s) => (
                  <TableRow key={s.patient_id}>
                    <TableCell className="font-mono text-xs">{s.patient_id}</TableCell>
                    <TableCell>{s.name ?? '—'}</TableCell>
                    <TableCell>{s.sex}</TableCell>
                    <TableCell>{s.age ?? '—'}</TableCell>
                    <TableCell className="text-xs text-gray-500">{s.updated_at}</TableCell>
                    <TableCell>
                      {onSelectPatientId && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => onSelectPatientId(s.patient_id)}
                        >
                          选择
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
