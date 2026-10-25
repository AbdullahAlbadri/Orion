"use client";

// Drag-and-drop / tap-to-upload for logos and artwork. Shows a thumbnail for images, a file chip otherwise.
import { useEffect, useRef, useState } from "react";

import { ApiError, fileObjectUrl, uploadFile, type UploadedFile } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { ImageIcon, PlusIcon } from "./Icons";

const ACCEPT = ".png,.jpg,.jpeg,.webp,.svg,.pdf,.ai,.eps,image/png,image/jpeg,image/webp,image/svg+xml,application/pdf";
const MAX_BYTES = 10 * 1024 * 1024;
const IMAGE = /^image\//;

export function FileThumb({ orderId, file }: { orderId: string; file: UploadedFile }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!IMAGE.test(file.content_type)) return;
    let alive = true;
    fileObjectUrl(orderId, file.file_id).then((u) => alive && setUrl(u)).catch(() => {});
    return () => { alive = false; };
  }, [orderId, file]);
  return url
    // eslint-disable-next-line @next/next/no-img-element
    ? <img className="thumb" src={url} alt={file.name} />
    : <span className="thumb thumb-doc"><ImageIcon /><span>{file.name.split(".").pop()?.toUpperCase()}</span></span>;
}

export default function FileUpload({ orderId, value, onChange, pictures }: {
  orderId: string; value: UploadedFile[]; onChange: (files: UploadedFile[]) => void;
  pictures?: boolean;   // reference pictures rather than a logo (only changes the wording)
}) {
  const { t } = useLang();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [over, setOver] = useState(false);

  async function add(list: FileList | null) {
    if (!list?.length) return;
    setBusy(true);
    setError(null);
    const added: UploadedFile[] = [];
    for (const file of Array.from(list)) {
      if (file.size > MAX_BYTES) { setError(t("fileTooBig")); continue; }
      try {
        added.push(await uploadFile(orderId, file));
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        setError(status === 415 ? t("fileWrongType") : status === 413 ? t("fileTooBig") : t("error"));
      }
    }
    if (added.length) onChange([...value, ...added]);
    setBusy(false);
    if (input.current) input.current.value = "";
  }

  return (
    <div className="upload">
      <div className={`dropzone${over ? " over" : ""}`} role="button" tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); } }}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}>
        <span className="dropzone-icon"><PlusIcon /></span>
        <strong>{busy ? t("uploading") : t(pictures ? "uploadCtaPictures" : "uploadCta")}</strong>
        <span className="muted small">{t("uploadTypes")}</span>
        <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(e) => add(e.target.files)} />
      </div>
      {error && <p className="error small">{error}</p>}
      {value.length > 0 && (
        <ul className="file-list">
          {value.map((f) => (
            <li key={f.file_id}>
              <FileThumb orderId={orderId} file={f} />
              <span className="file-name" dir="auto">{f.name}</span>
              <button type="button" className="icon-btn" aria-label={t("remove")}
                onClick={() => onChange(value.filter((x) => x.file_id !== f.file_id))}>×</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
