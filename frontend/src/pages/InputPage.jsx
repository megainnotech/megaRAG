
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Loader2, GitBranch, Upload, FileUp, X, Github, Plus } from 'lucide-react';

const STANDARD_TAGS = ['app_name', 'version', 'business_name', 'application', 'payment'];

const InputPage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);

    // Git State
    const [gitUrl, setGitUrl] = useState('');
    const [branch, setBranch] = useState('main');
    const [gitTags, setGitTags] = useState([{ key: '', value: '' }]);

    // File State
    const [file, setFile] = useState(null);
    const [fileTags, setFileTags] = useState([{ key: '', value: '' }]);

    const onDrop = useCallback(acceptedFiles => {
        if (acceptedFiles?.length > 0) {
            setFile(acceptedFiles[0]);
            toast.success(`Selected file: ${acceptedFiles[0].name}`);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        multiple: false,
        accept: {
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt', '.md'],
            'application/zip': ['.zip']
        }
    });

    const handleTagChange = (index, field, value, setTags) => {
        setTags(prev => {
            const newTags = [...prev];
            newTags[index][field] = value;
            return newTags;
        });
    };

    const addTag = (setTags) => {
        setTags(prev => [...prev, { key: '', value: '' }]);
    };

    const removeTag = (index, setTags) => {
        setTags(prev => {
            if (prev.length === 1 && index === 0) return [{ key: '', value: '' }];
            const newTags = [...prev];
            newTags.splice(index, 1);
            return newTags;
        });
    };

    const formatTags = (tagsList) => {
        const tagObj = {};
        tagsList.forEach(t => {
            if (t.key && t.value) {
                tagObj[t.key] = t.value;
            }
        });
        return tagObj;
    };

    const handleGitSubmit = async (e) => {
        e.preventDefault();
        if (!gitUrl) {
            toast.error("Please enter a Git URL");
            return;
        }

        setLoading(true);
        try {
            const response = await fetch('http://localhost:3001/api/documents/git', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: gitUrl,
                    branch,
                    tags: formatTags(gitTags)
                })
            });

            const data = await response.json();
            if (response.ok) {
                toast.success('Git repository processed successfully!');
                setTimeout(() => navigate('/'), 1500);
            } else {
                toast.error(data.message || 'Failed to process repository');
            }
        } catch (error) {
            toast.error('Network error or server unreachable');
        } finally {
            setLoading(false);
        }
    };

    const handleFileSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            toast.warning('Please select a file');
            return;
        }
        setLoading(true);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('tags', JSON.stringify(formatTags(fileTags)));

        try {
            const response = await fetch('http://localhost:3001/api/documents/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                toast.success('File uploaded successfully!');
                setTimeout(() => navigate('/'), 1500);
            } else {
                toast.error(data.message || 'Failed to upload file');
            }
        } catch (error) {
            toast.error('Network error or server unreachable');
        } finally {
            setLoading(false);
        }
    };

    const TagInputs = ({ tags, setTags, idPrefix }) => (
        <div className="space-y-3">
            <Label>Tags</Label>
            {tags.map((tag, index) => (
                <div key={index} className="flex items-center gap-2">
                    <div className="grid grid-cols-2 gap-2 flex-1">
                        <Input
                            placeholder="Key"
                            list={`tags-${idPrefix}`}
                            value={tag.key}
                            onChange={(e) => handleTagChange(index, 'key', e.target.value, setTags)}
                        />
                        <datalist id={`tags-${idPrefix}`}>
                            {STANDARD_TAGS.map(t => <option key={t} value={t} />)}
                        </datalist>
                        <Input
                            placeholder="Value"
                            value={tag.value}
                            onChange={(e) => handleTagChange(index, 'value', e.target.value, setTags)}
                        />
                    </div>
                    {tags.length > 0 && (
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeTag(index, setTags)}
                            className="text-muted-foreground hover:text-destructive"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            ))}
            <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addTag(setTags)}
                className="w-full border-dashed"
            >
                <Plus className="mr-2 h-3.5 w-3.5" /> Add Tag
            </Button>
        </div>
    );

    return (
        <div className="mx-auto max-w-2xl space-y-8">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Add Document</h1>
                <p className="text-muted-foreground">
                    Import new documentation from a Git repository or upload files directly.
                </p>
            </div>

            <Tabs defaultValue="git" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-8">
                    <TabsTrigger value="git">Git Import</TabsTrigger>
                    <TabsTrigger value="file">File Upload</TabsTrigger>
                </TabsList>

                <TabsContent value="git">
                    <Card>
                        <CardHeader>
                            <CardTitle>Git Repository</CardTitle>
                            <CardDescription>
                                Import documentation directly from a remote Git repository.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleGitSubmit} className="space-y-6">
                                <div className="space-y-2">
                                    <Label htmlFor="git-url">Repository URL</Label>
                                    <div className="relative">
                                        <Github className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                        <Input
                                            id="git-url"
                                            placeholder="https://github.com/username/repo.git"
                                            className="pl-9"
                                            value={gitUrl}
                                            onChange={(e) => setGitUrl(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="git-branch">Branch</Label>
                                    <div className="relative">
                                        <GitBranch className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                        <Input
                                            id="git-branch"
                                            placeholder="main"
                                            className="pl-9"
                                            value={branch}
                                            onChange={(e) => setBranch(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <TagInputs tags={gitTags} setTags={setGitTags} idPrefix="git" />

                                <Button type="submit" className="w-full" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Import Repository
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="file">
                    <Card>
                        <CardHeader>
                            <CardTitle>File Upload</CardTitle>
                            <CardDescription>
                                Upload PDF, Markdown, or ZIP files containing documentation.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <form onSubmit={handleFileSubmit} className="space-y-6">
                                <div
                                    {...getRootProps()}
                                    className={`
                                        border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors
                                        ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
                                    `}
                                >
                                    <input {...getInputProps()} />
                                    <div className="flex flex-col items-center gap-2">
                                        <div className="p-3 rounded-full bg-muted">
                                            <Upload className="h-6 w-6 text-muted-foreground" />
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-sm font-medium">
                                                {file ? file.name : "Drag & drop or click to upload"}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                Supports PDF, Markdown, TXT, ZIP
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <TagInputs tags={fileTags} setTags={setFileTags} idPrefix="file" />

                                <Button type="submit" className="w-full" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    {file ? 'Upload File' : 'Select File'}
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default InputPage;
