import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings2, Save } from 'lucide-react';
import { toast } from 'sonner';

const ConfigPage = () => {
    // LLM Settings
    const [llmType, setLlmType] = useState('local'); // 'local' or 'public'
    const [apiKey, setApiKey] = useState('');
    const [baseUrl, setBaseUrl] = useState('http://localhost:11434/v1');
    const [modelName, setModelName] = useState('llama3');

    // Load saved config on mount
    useEffect(() => {
        const savedConfig = localStorage.getItem('rag_llm_config');
        if (savedConfig) {
            try {
                const parsed = JSON.parse(savedConfig);
                setLlmType(parsed.type || 'local');
                setApiKey(parsed.apiKey || '');
                setBaseUrl(parsed.baseUrl || 'http://localhost:11434/v1');
                setModelName(parsed.model || 'llama3');
            } catch (e) {
                console.error("Failed to parse saved config", e);
            }
        }
    }, []);

    const handleSaveConfig = () => {
        const config = {
            type: llmType,
            apiKey,
            baseUrl,
            model: modelName
        };
        localStorage.setItem('rag_llm_config', JSON.stringify(config));
        toast.success("Configuration saved successfully!");
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
            </div>

            <div className="grid gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Settings2 className="h-5 w-5" />
                            LLM Configuration
                        </CardTitle>
                        <CardDescription>
                            Configure the Language Model used for RAG generation.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6 max-w-2xl">
                        <div className="space-y-4">
                            <Label>Provider Type</Label>
                            <Tabs value={llmType} onValueChange={setLlmType} className="w-full">
                                <TabsList className="grid w-full grid-cols-2">
                                    <TabsTrigger value="local">Local (Ollama/LM Studio)</TabsTrigger>
                                    <TabsTrigger value="public">Public (OpenAI)</TabsTrigger>
                                </TabsList>
                            </Tabs>

                            {llmType === 'local' && (
                                <div className="space-y-4 pt-2 animate-in fade-in slide-in-from-top-2">
                                    <div className="space-y-2">
                                        <Label>Base URL</Label>
                                        <Input
                                            placeholder="http://localhost:11434/v1"
                                            value={baseUrl}
                                            onChange={(e) => setBaseUrl(e.target.value)}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Default for Ollama: http://localhost:11434/v1
                                        </p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Model Name</Label>
                                        <Input
                                            placeholder="llama3"
                                            value={modelName}
                                            onChange={(e) => setModelName(e.target.value)}
                                        />
                                    </div>
                                </div>
                            )}

                            {llmType === 'public' && (
                                <div className="space-y-2 pt-2 animate-in fade-in slide-in-from-top-2">
                                    <Label>Model Name</Label>
                                    <Input
                                        placeholder="gpt-4o-mini"
                                        value={modelName}
                                        onChange={(e) => setModelName(e.target.value)}
                                    />
                                </div>
                            )}

                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label>API Key / Token</Label>
                                    <span className="text-xs text-muted-foreground">Optional for some local LLMs</span>
                                </div>
                                <Input
                                    type="password"
                                    placeholder={llmType === 'public' ? "sk-..." : "Configured in server or leave empty"}
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                />
                            </div>

                            <Button onClick={handleSaveConfig} className="w-full md:w-auto">
                                <Save className="mr-2 h-4 w-4" />
                                Save Configuration
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Placeholder for future configs */}
                <Card>
                    <CardHeader>
                        <CardTitle>Other Settings</CardTitle>
                        <CardDescription>System-wide configurations (Coming Soon)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-muted-foreground">Additional settings for Retrieval logic, Search thresholds, etc. will appear here.</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ConfigPage;
