import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Send, Bot, User, Settings2 } from 'lucide-react';
import { toast } from 'sonner';

const RetrievePage = () => {
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);
    const [mode, setMode] = useState('hybrid');

    // LLM Settings
    const [llmType, setLlmType] = useState('local'); // 'local' or 'public'
    const [apiKey, setApiKey] = useState('');

    const handleQuery = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResponse(''); // Clear previous response

        try {
            const res = await fetch('http://localhost:3001/api/documents/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    mode,
                    llmConfig: { type: llmType, apiKey } // Pass config if supported by backend/rag
                })
            });

            if (!res.ok) throw new Error('Failed to query RAG');

            const data = await res.json();
            setResponse(data.response || "No response generated.");
        } catch (error) {
            toast.error(error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="mx-auto max-w-4xl space-y-8">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Retrieve Knowledge</h1>
            </div>

            <div className="grid gap-6 md:grid-cols-[300px_1fr]">
                {/* Settings Sidebar */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Settings2 className="h-5 w-5" />
                                Configuration
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label>Search Mode</Label>
                                <Tabs value={mode} onValueChange={setMode} className="w-full">
                                    <TabsList className="grid w-full grid-cols-3">
                                        <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
                                        <TabsTrigger value="vector">Vector</TabsTrigger>
                                        <TabsTrigger value="graph">Graph</TabsTrigger>
                                    </TabsList>
                                </Tabs>
                            </div>

                            <div className="space-y-2">
                                <Label>LLM Provider</Label>
                                <Tabs value={llmType} onValueChange={setLlmType} className="w-full">
                                    <TabsList className="grid w-full grid-cols-2">
                                        <TabsTrigger value="local">Local</TabsTrigger>
                                        <TabsTrigger value="public">Public</TabsTrigger>
                                    </TabsList>
                                </Tabs>
                            </div>

                            {llmType === 'public' && (
                                <div className="space-y-2">
                                    <Label>API Key (OpenAI/Gemini)</Label>
                                    <Input
                                        type="password"
                                        placeholder="sk-..."
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                    />
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Chat Area */}
                <Card className="flex flex-col h-[600px]">
                    <CardContent className="flex-1 overflow-y-auto p-6 space-y-4">
                        {/* Placeholder / Empty State */}
                        {!response && !loading && (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                                <Bot className="h-12 w-12 mb-4" />
                                <p>Ask a question to search the knowledge base.</p>
                            </div>
                        )}

                        {/* User Query Display (Optional, if chat history style) */}
                        {/* For now, just showing latest Q&A */}

                        {response && (
                            <div className="bg-muted/50 p-4 rounded-lg">
                                <p className="leading-relaxed whitespace-pre-wrap">{response}</p>
                            </div>
                        )}

                        {loading && (
                            <div className="flex items-center gap-2 text-muted-foreground p-4">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span>Thinking...</span>
                            </div>
                        )}
                    </CardContent>

                    <div className="p-4 border-t bg-background">
                        <form onSubmit={handleQuery} className="flex gap-2">
                            <Input
                                placeholder="What is the architecture of..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                disabled={loading}
                            />
                            <Button type="submit" disabled={loading || !query.trim()}>
                                <Send className="h-4 w-4" />
                            </Button>
                        </form>
                    </div>
                </Card>
            </div>
        </div>
    );
};

export default RetrievePage;
