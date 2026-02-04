export function ClinicalIframeView() {
  const clinicalUrl = import.meta.env.VITE_CLINICAL_URL ?? '';
  if (clinicalUrl) {
    return (
      <div className="flex-1 bg-white">
        <iframe
          title="CPET 在线监测"
          src={clinicalUrl}
          className="w-full h-full min-h-screen border-0"
        />
      </div>
    );
  }

  const backendOrigin = import.meta.env.VITE_BACKEND_ORIGIN ?? '';
  const apiBase = import.meta.env.VITE_API_BASE ?? '';
  const resolvedBase =
    backendOrigin ||
    (apiBase.startsWith('http://') || apiBase.startsWith('https://') ? apiBase : '');
  const baseOrigin = resolvedBase
    ? new URL(resolvedBase, window.location.origin).origin
    : window.location.origin;
  const src = `${baseOrigin}/app/clinical.html`;
  return (
    <div className="flex-1 bg-white">
      <iframe
        title="CPET 在线监测"
        src={src}
        className="w-full h-full min-h-screen border-0"
      />
    </div>
  );
}
