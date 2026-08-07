import type { ReactNode } from "react";

import { getResultText, parseInput, toolArgClass, toolLabelClass } from "./_shared";
import { FileAttachment } from "@/components/chat/FileAttachment";
import type { TFunction, ToolCallWithResult } from "./types";

interface GeneratedFile {
    path: string;
    name: string;
}

export const RunPythonRenderer = {
    renderHeader(pair: ToolCallWithResult, _t: TFunction): ReactNode {
        const { script_path } = parseInput(pair.call.input) as {
            script_path?: string;
        };
        const fileName = script_path
            ? script_path.split(/[/\\]+/).filter(Boolean).pop() ?? script_path
            : undefined;
        return (
            <>
                <span className={toolLabelClass}>RunPython</span>
                {fileName && <span className={toolArgClass}>{fileName}</span>}
            </>
        );
    },

    renderBody(pair: ToolCallWithResult, _t: TFunction): ReactNode {
        const { result } = pair;
        if (!result) return null;

        const metadata = result.metadata as Record<string, unknown> | undefined;
        const generatedFiles = (
            Array.isArray(metadata?.generated_files)
                ? (metadata.generated_files as GeneratedFile[])
                : []
        ).filter(
            (f): f is GeneratedFile =>
                typeof f === "object" && f !== null && typeof f.path === "string",
        );

        const outputText = getResultText(result);

        function getMediaType(fileName: string): string {
            const ext = fileName.split(".").pop()?.toLowerCase();
            switch (ext) {
                case "xlsx":
                    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
                case "xls":
                    return "application/vnd.ms-excel";
                case "docx":
                    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
                case "pptx":
                    return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
                case "pdf":
                    return "application/pdf";
                case "csv":
                    return "text/csv";
                case "json":
                    return "application/json";
                case "png":
                    return "image/png";
                case "jpg":
                case "jpeg":
                    return "image/jpeg";
                case "svg":
                    return "image/svg+xml";
                default:
                    return "application/octet-stream";
            }
        }

        return (
            <div className="space-y-2">
                {outputText && (
                    <pre className="border rounded-sm bg-background p-2 text-xs overflow-auto max-h-[200px] whitespace-pre-wrap">
                        {outputText}
                    </pre>
                )}
                {generatedFiles.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                        {generatedFiles.map((file) => {
                            const downloadUrl = `/api/file/download?path=${encodeURIComponent(file.path)}&filename=${encodeURIComponent(file.name)}`;
                            return (
                                <FileAttachment
                                    key={file.path}
                                    name={file.name}
                                    href={downloadUrl}
                                    mediaType={getMediaType(file.name)}
                                />
                            );
                        })}
                    </div>
                )}
            </div>
        );
    },
};
