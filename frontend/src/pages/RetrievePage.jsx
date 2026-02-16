import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Send, Bot, User, Settings2 } from 'lucide-react';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const RetrievePage = () => {
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState('hybrid');
    const [statusMessage, setStatusMessage] = useState('');
    const [sources, setSources] = useState([]);

    const handleQuery = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResponse(''); // Clear previous response
        setSources([]); // Clear previous sources
        setStatusMessage('Initializing...');

        try {
            // Read config from local storage at request time
            const savedConfig = localStorage.getItem('rag_llm_config');
            let config = {};
            if (savedConfig) {
                try {
                    config = JSON.parse(savedConfig);
                } catch (e) {
                    console.error("Failed to parse config", e);
                }
            }

            const res = await fetch('http://localhost:3001/api/documents/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    mode,
                    llmConfig: config // Use loaded config
                })
            });

            if (!res.ok) throw new Error('Failed to query RAG');

            // Stream reading logic
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                // Parse SSE format: data: {...}
                const lines = chunk.split('\n\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (data.type === 'status') {
                                setStatusMessage(data.content);
                            } else if (data.type === 'answer') {
                                accumulatedResponse = data.content;
                                setResponse(accumulatedResponse);
                                // We keep loading true until done? Or stream might continue?
                                // Usually answer is final. But let's keep loading until loop finishes.
                            } else if (data.type === 'sources') {
                                setSources(data.content);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data', e);
                        }
                    }
                }
            }

        } catch (error) {
            toast.error(error.message);
            setResponse(prev => prev || "Error generating response.");
        } finally {
            setLoading(false);
            setStatusMessage('');
        }
    };



    return (
        <div className="flex flex-col h-[calc(100vh-theme(spacing.16))] gap-4 p-4 md:p-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold tracking-tight">Retrieve Knowledge</h1>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-1 gap-6 h-full overflow-hidden">
                {/* Settings Sidebar - Removed, moved to /config page */}

                {/* Chat Area - Full Width */}
                <Card className="flex flex-col h-full overflow-hidden border-none shadow-md md:border col-span-1">
                    <CardContent className="flex-1 overflow-y-auto p-6 space-y-6">
                        {/* Internal Config Area (Search Mode only) */}
                        <div className="flex justify-end mb-4">
                            <Tabs value={mode} onValueChange={setMode} className="w-[400px]">
                                <TabsList className="grid w-full grid-cols-4">
                                    <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
                                    <TabsTrigger value="vector">Vector</TabsTrigger>
                                    <TabsTrigger value="graph">Graph</TabsTrigger>
                                    <TabsTrigger value="direct">Direct LLM</TabsTrigger>
                                </TabsList>
                            </Tabs>
                        </div>

                        {/* Chat Area */}

                        {/* Placeholder / Empty State */}
                        {!response && !loading && (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50 space-y-4">
                                <div className="p-4 rounded-full bg-muted">
                                    <Bot className="h-12 w-12" />
                                </div>
                                <div className="text-center">
                                    <h3 className="font-semibold text-lg">Knowledge Base Assistant</h3>
                                    <p className="text-sm">Ask any question to retrieve context from your documents.</p>
                                </div>
                            </div>
                        )}

                        {/* Response Area */}
                        {response && (
                            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2">
                                <div className="flex items-start gap-4">
                                    <div className="p-2 rounded-full bg-primary/10 text-primary mt-1">
                                        <Bot className="h-5 w-5" />
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <div className="prose prose-sm dark:prose-invert max-w-none p-4 rounded-lg bg-muted/30 border overflow-x-auto">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {response}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                </div>

                                {/* Sources Display */}
                                {sources && sources.length > 0 && (
                                    <div className="ml-11 p-4 rounded-lg bg-muted/20 border text-sm">
                                        <h4 className="font-semibold mb-2 text-muted-foreground">Sources:</h4>
                                        <ul className="space-y-1">
                                            {sources.map((source, index) => (
                                                <li key={index} className="flex items-center gap-2">
                                                    <span className="text-muted-foreground w-4 text-center">{index + 1}.</span>
                                                    <a
                                                        href={source.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="text-blue-600 hover:underline break-all"
                                                    >
                                                        {source.url}
                                                    </a>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}

                        {loading && (
                            <div className="flex items-center justify-center h-full">
                                <div className="flex flex-col items-center gap-4 text-muted-foreground animate-pulse">
                                    <Loader2 className="h-8 w-8 animate-spin" />
                                    <span>{statusMessage || 'Processing your query...'}</span>
                                </div>
                            </div>
                        )}
                    </CardContent>

                    <div className="p-4 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                        <form onSubmit={handleQuery} className="flex gap-4 max-w-3xl mx-auto w-full">
                            <Input
                                placeholder="Ask a question about your documents..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                disabled={loading}
                                className="flex-1"
                            />
                            <Button type="submit" disabled={loading || !query.trim()} className="px-6">
                                <Send className="h-4 w-4 mr-2" />
                                Ask
                            </Button>
                        </form>
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default RetrievePage;
