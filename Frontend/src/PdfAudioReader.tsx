import { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface Props {
  fileUrl: string;
  audioUrl: string;
}

export default function PdfAudioReader({ fileUrl, audioUrl }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [numPages, setNumPages] = useState<number>();
  const [page, setPage] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handle = () => {
      if (!numPages || !audio.duration) return;
      const newPage = Math.floor((audio.currentTime / audio.duration) * numPages) + 1;
      if (newPage !== page) setPage(newPage);
    };
    audio.addEventListener('timeupdate', handle);
    return () => audio.removeEventListener('timeupdate', handle);
  }, [numPages, page]);

  return (
    <div>
      <audio controls src={audioUrl} ref={audioRef} style={{ width: '100%' }} />
      <div style={{ marginTop: 16 }}>
        <Document file={fileUrl} onLoadSuccess={({ numPages }) => setNumPages(numPages)}>
          <Page pageNumber={page} width={600} />
        </Document>
      </div>
    </div>
  );
}
