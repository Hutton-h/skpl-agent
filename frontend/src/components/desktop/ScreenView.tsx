/**
 * ScreenView — Desktop screenshot viewer with annotation overlay.
 *
 * Displays a desktop screenshot with optional bounding box overlays
 * for detected UI elements. Supports zoom, pan, and element selection.
 *
 * Features:
 * - Base64 image rendering
 * - Bounding box overlay rendering
 * - Element hover/highlight
 * - Click coordinate capture
 * - Zoom controls
 */
import { cn } from '@/lib/utils';
import { useTranslation } from '@/i18n/useI18n';
import { Maximize2, Minimize2, RefreshCw, ZoomIn, ZoomOut } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';

/**
 * Represents a UI element bounding box.
 */
export interface ElementBBox {
  index: number;
  label: string;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  confidence?: number;
  type?: string;
}

/**
 * Coordinates of a click on the screenshot.
 */
export interface ClickCoordinate {
  x: number;
  y: number;
  relativeX: number;
  relativeY: number;
}

interface ScreenViewProps {
  /** Base64-encoded image (JPEG/PNG) */
  imageBase64: string;
  /** Image format */
  imageFormat?: 'jpeg' | 'png';
  /** Detected UI elements with bounding boxes */
  elements?: ElementBBox[];
  /** Whether to show element labels */
  showLabels?: boolean;
  /** Whether to show confidence scores */
  showConfidence?: boolean;
  /** Callback when user clicks on the screenshot */
  onClick?: (coord: ClickCoordinate) => void;
  /** Callback when user hovers over an element */
  onElementHover?: (element: ElementBBox | null) => void;
  /** Callback to request a screenshot refresh */
  onRefresh?: () => void;
  /** Whether the screenshot is loading */
  loading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Image width (used for aspect ratio) */
  imageWidth?: number;
  /** Image height (used for aspect ratio) */
  imageHeight?: number;
}

/** Color palette for bounding boxes */
const BBOX_COLORS = [
  '#FF3B30', '#34C759', '#007AFF', '#FF9500',
  '#AF52DE', '#FF2D55', '#5856D6', '#00C7BE',
  '#FFD60A', '#8E8E93',
];

export function ScreenView({
  imageBase64,
  imageFormat = 'jpeg',
  elements = [],
  showLabels = true,
  showConfidence = false,
  onClick,
  onElementHover,
  onRefresh,
  loading = false,
  className,
  imageWidth = 1920,
  imageHeight = 1080,
}: ScreenViewProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [hoveredElement, setHoveredElement] = useState<ElementBBox | null>(null);
  const [selectedElement, setSelectedElement] = useState<ElementBBox | null>(null);

  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(z + 0.25, 3));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(z - 0.25, 0.5));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 1 || (e.button === 0 && e.altKey)) {
        setIsPanning(true);
        setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
        e.preventDefault();
      }
    },
    [pan],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isPanning) {
        setPan({
          x: e.clientX - panStart.x,
          y: e.clientY - panStart.y,
        });
      }
    },
    [isPanning, panStart],
  );

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  const handleImageClick = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      if (isPanning) return;
      const img = imageRef.current;
      if (!img || !onClick) return;

      const rect = img.getBoundingClientRect();
      const x = (e.clientX - rect.left) / zoom;
      const y = (e.clientY - rect.top) / zoom;
      const displayWidth = rect.width / zoom;
      const displayHeight = rect.height / zoom;

      onClick({
        x: Math.round((x / displayWidth) * imageWidth),
        y: Math.round((y / displayHeight) * imageHeight),
        relativeX: x / displayWidth,
        relativeY: y / displayHeight,
      });
    },
    [isPanning, onClick, zoom, imageWidth, imageHeight],
  );

  const handleElementClick = useCallback(
    (element: ElementBBox) => {
      setSelectedElement(
        selectedElement?.index === element.index ? null : element,
      );
    },
    [selectedElement],
  );

  const handleElementEnter = useCallback(
    (element: ElementBBox) => {
      setHoveredElement(element);
      onElementHover?.(element);
    },
    [onElementHover],
  );

  const handleElementLeave = useCallback(() => {
    setHoveredElement(null);
    onElementHover?.(null);
  }, [onElementHover]);

  const srcUrl = imageBase64
    ? `data:image/${imageFormat};base64,${imageBase64}`
    : '';

  return (
    <div className={cn('relative overflow-hidden rounded-lg bg-background', className)}>
      {/* Toolbar */}
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1 rounded-md bg-background/80 p-1 backdrop-blur-sm">
        <button
          type="button"
          onClick={handleZoomIn}
          className="rounded p-1 hover:bg-accent hover:text-accent-foreground"
          title={t('desktop.zoomIn')}
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="rounded p-1 hover:bg-accent hover:text-accent-foreground"
          title={t('desktop.zoomOut')}
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomReset}
          className="rounded p-1 hover:bg-accent hover:text-accent-foreground"
          title={t('desktop.resetZoom')}
        >
          <Minimize2 className="h-4 w-4" />
        </button>
        <div className="mx-1 h-4 w-px bg-border" />
        <span className="px-1 text-xs text-muted-foreground tabular-nums">
          {Math.round(zoom * 100)}%
        </span>
        {onRefresh && (
          <>
            <div className="mx-1 h-4 w-px bg-border" />
            <button
              type="button"
              onClick={onRefresh}
              className="rounded p-1 hover:bg-accent hover:text-accent-foreground"
              title={t('desktop.refreshScreenshot')}
            >
              <RefreshCw
                className={cn('h-4 w-4', loading && 'animate-spin')}
              />
            </button>
          </>
        )}
      </div>

      {/* Image container */}
      <div
        ref={containerRef}
        className={cn(
          'relative flex items-center justify-center overflow-hidden',
          'min-h-[200px] bg-muted/30',
          isPanning && 'cursor-grabbing',
          !isPanning && onClick && 'cursor-crosshair',
        )}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {loading ? (
          <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
            <RefreshCw className="h-8 w-8 animate-spin" />
            <span className="text-sm">{t('desktop.loadingScreenshot')}</span>
          </div>
        ) : srcUrl ? (
          <div
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
            }}
          >
            <img
              ref={imageRef}
              src={srcUrl}
              alt={t('desktop.screenshot')}
              className="max-w-none select-none"
              style={{ width: imageWidth, height: 'auto' }}
              onClick={handleImageClick}
              draggable={false}
            />

            {/* Bounding box overlay */}
            {elements.length > 0 && (
              <svg
                className="absolute inset-0 pointer-events-none"
                width={imageWidth}
                height={imageHeight}
                style={{ top: 0, left: 0 }}
              >
                {elements.map((elem, i) => {
                  const [x1, y1, x2, y2] = elem.bbox;
                  const w = x2 - x1;
                  const h = y2 - y1;
                  const isHovered = hoveredElement?.index === elem.index;
                  const isSelected = selectedElement?.index === elem.index;
                  const color = BBOX_COLORS[i % BBOX_COLORS.length];

                  return (
                    <g key={elem.index ?? i}>
                      {/* Invisible hit area for hover */}
                      <rect
                        x={x1}
                        y={y1}
                        width={w}
                        height={h}
                        fill="transparent"
                        className="pointer-events-auto cursor-pointer"
                        onMouseEnter={() => handleElementEnter(elem)}
                        onMouseLeave={handleElementLeave}
                        onClick={() => handleElementClick(elem)}
                      />
                      {/* Visible bounding box */}
                      <rect
                        x={x1}
                        y={y1}
                        width={w}
                        height={h}
                        fill="none"
                        stroke={color}
                        strokeWidth={isHovered || isSelected ? 3 : 1.5}
                        strokeOpacity={isHovered || isSelected ? 1 : 0.7}
                        rx={2}
                      />
                      {/* Label */}
                      {(showLabels && (isHovered || isSelected)) && (
                        <>
                          <rect
                            x={x1}
                            y={Math.max(0, y1 - 18)}
                            width={w}
                            height={18}
                            fill={color}
                            rx={2}
                          />
                          <text
                            x={x1 + 4}
                            y={Math.max(0, y1 - 5)}
                            fill="#fff"
                            fontSize={11}
                            fontFamily="monospace"
                          >
                            {showConfidence && elem.confidence != null
                              ? `${elem.label} (${(elem.confidence * 100).toFixed(0)}%)`
                              : elem.label}
                          </text>
                        </>
                      )}
                      {/* Index badge */}
                      <circle
                        cx={x1 + 8}
                        cy={y1 + 8}
                        r={8}
                        fill={color}
                        stroke="#fff"
                        strokeWidth={1}
                      />
                      <text
                        x={x1 + 8}
                        y={y1 + 11}
                        fill="#fff"
                        fontSize={9}
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {elem.index}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
            <Maximize2 className="h-8 w-8" />
            <span className="text-sm">{t('desktop.noScreenshot')}</span>
          </div>
        )}
      </div>

      {/* Element info bar */}
      {hoveredElement && (
        <div className="absolute bottom-2 left-2 right-2 rounded-md bg-background/90 px-3 py-1.5 text-xs backdrop-blur-sm">
          <span className="font-mono font-semibold">
            #{hoveredElement.index}
          </span>
          <span className="ml-2 text-muted-foreground">
            {hoveredElement.label}
          </span>
          {hoveredElement.type && (
            <span className="ml-2 rounded bg-muted px-1 py-0.5 text-[10px]">
              {hoveredElement.type}
            </span>
          )}
          <span className="ml-2 text-muted-foreground">
            [{hoveredElement.bbox.join(', ')}]
          </span>
          {hoveredElement.confidence != null && (
            <span className="ml-2 tabular-nums">
              {(hoveredElement.confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default ScreenView;