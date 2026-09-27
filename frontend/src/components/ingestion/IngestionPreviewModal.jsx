import React from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  Layers,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Table,
  Cpu,
  ArrowRight,
  Maximize2
} from "lucide-react";
import { Link } from "react-router-dom";

export default function IngestionPreviewModal({ isOpen, onClose, metadata, fileName }) {
  const { t } = useTranslation();

  if (!isOpen || !metadata) return null;

  const isMapReady = metadata.map_ready;
  const isMlReady = metadata.ml_ready;
  const columns = metadata.columns || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-sm">
              <Layers size={18} />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">
                {t("preview.title", "Dataset Ingestion Inspection")}
              </h3>
              <p className="text-xs text-slate-500 font-mono truncate max-w-md">
                {fileName || "Dataset Details"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 rounded-lg transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Key Stat Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <span className="text-[11px] font-medium text-slate-500 block mb-1">
                {t("preview.fileType", "Format")}
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                {metadata.format || "Unknown"}
              </span>
            </div>

            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <span className="text-[11px] font-medium text-slate-500 block mb-1">
                {t("preview.crs", "Detected CRS")}
              </span>
              <span className={`text-xs font-semibold font-mono ${metadata.crs ? "text-slate-800" : "text-amber-600"}`}>
                {metadata.crs || "Unprojected / None"}
              </span>
            </div>

            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <span className="text-[11px] font-medium text-slate-500 block mb-1">
                {t("preview.featureCount", "Records / Bands")}
              </span>
              <span className="text-xs font-bold text-slate-800 font-mono">
                {metadata.feature_count !== null && metadata.feature_count !== undefined
                  ? metadata.feature_count.toLocaleString()
                  : "N/A"}
              </span>
            </div>

            <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
              <span className="text-[11px] font-medium text-slate-500 block mb-1">
                {t("preview.geometryType", "Geometry")}
              </span>
              <span className="text-xs font-medium text-slate-700 truncate block">
                {metadata.geometry_type || "Attribute/Raster"}
              </span>
            </div>
          </div>

          {/* Readiness Indicators */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className={`p-3 rounded-xl border flex items-center gap-3 ${
              isMapReady ? "bg-emerald-50/60 border-emerald-200 text-emerald-900" : "bg-amber-50/60 border-amber-200 text-amber-900"
            }`}>
              {isMapReady ? <CheckCircle2 size={20} className="text-emerald-600 shrink-0" /> : <AlertTriangle size={20} className="text-amber-600 shrink-0" />}
              <div className="text-xs">
                <span className="font-semibold block">
                  {t("preview.mapReady", "Map Ready")}: {isMapReady ? t("preview.yes", "Yes") : t("preview.no", "No")}
                </span>
                <span className="text-[11px] opacity-80">
                  {isMapReady ? "Valid spatial projection ready for GIS overlay." : "Requires GCP Georeferencing or coordinates."}
                </span>
              </div>
            </div>

            <div className={`p-3 rounded-xl border flex items-center gap-3 ${
              isMlReady ? "bg-indigo-50/60 border-indigo-200 text-indigo-900" : "bg-slate-50 border-slate-200 text-slate-700"
            }`}>
              <Cpu size={20} className={isMlReady ? "text-indigo-600 shrink-0" : "text-slate-400 shrink-0"} />
              <div className="text-xs">
                <span className="font-semibold block">
                  {t("preview.mlReady", "ML Harmonization Ready")}: {isMlReady ? t("preview.yes", "Yes") : t("preview.no", "No")}
                </span>
                <span className="text-[11px] opacity-80">
                  {isMlReady ? "Spatial topology and features available for matching." : "Additional features or alignment needed."}
                </span>
              </div>
            </div>
          </div>

          {/* Bounds Info */}
          {metadata.bounds && (
            <div className="bg-slate-50/80 rounded-xl p-3 border border-slate-200 text-xs">
              <span className="font-medium text-slate-700 block mb-1">Spatial Extent / Bounding Box</span>
              <div className="font-mono text-[11px] text-slate-600 grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div>Min X: {Number(metadata.bounds.min_x).toFixed(5)}</div>
                <div>Min Y: {Number(metadata.bounds.min_y).toFixed(5)}</div>
                <div>Max X: {Number(metadata.bounds.max_x).toFixed(5)}</div>
                <div>Max Y: {Number(metadata.bounds.max_y).toFixed(5)}</div>
              </div>
            </div>
          )}

          {/* Detected Attributes / Columns */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Table size={14} className="text-slate-400" />
              <span className="text-xs font-semibold text-slate-700">
                {t("preview.columns", "Detected Attributes / Columns")} ({columns.length})
              </span>
            </div>
            {columns.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                {columns.map((col, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 bg-white border border-slate-200 rounded text-[11px] font-mono text-slate-700 shadow-2xs"
                  >
                    {col}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No tabular attribute fields detected.</p>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-100 bg-slate-50/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            {t("common.close", "Close")}
          </button>
          <div className="flex items-center gap-2">
            <Link
              to="/map"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs transition-colors"
            >
              <MapPin size={14} />
              {t("nav.map", "GIS Map Viewer")}
            </Link>
            <Link
              to="/harmonization"
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-sm transition-colors"
            >
              {t("nav.harmonization", "Harmonization")}
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
