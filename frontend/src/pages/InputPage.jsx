
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



    return (
        <div className="container mx-auto p-6 max-w-[1600px] h-full">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
                {/* Header Side */}
                <div className="lg:col-span-4 space-y-6">
                    <div className="space-y-4">
                        <h1 className="text-4xl font-bold tracking-tight">Add Documents</h1>
                        <p className="text-muted-foreground text-lg">
                            Build your knowledge base by importing from Git or uploading files.
                            Supported formats include PDF, Markdown, and ZIP archives.
                        </p>
                    </div>

                    <div className="bg-muted/40 p-6 rounded-lg border border-dashed">
                        <h3 className="font-semibold mb-2">Supported Features</h3>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                            <li className="flex items-center gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                                Automatic Recursive MKDocs parsing
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                                PDF text extraction & OCR
                            </li>
                            <li className="flex items-center gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                                Metadata tagging for Git imports
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Content Side */}
                <div className="lg:col-span-8">
                    <Tabs defaultValue="git" className="w-full h-full flex flex-col">
                        <TabsList className="grid w-full grid-cols-2 h-12 mb-6">
                            <TabsTrigger value="git" className="text-base">Git Import</TabsTrigger>
                            <TabsTrigger value="file" className="text-base">File Upload</TabsTrigger>
                        </TabsList>

                        <div className="flex-1 bg-background border rounded-xl shadow-sm p-6 md:p-8">
                            <TabsContent value="git" className="mt-0 space-y-6">
                                <div className="space-y-2 mb-6">
                                    <h2 className="text-2xl font-semibold">Git Repository</h2>
                                    <p className="text-muted-foreground">Clone and ingest documentation directly from remote repositories.</p>
                                </div>
                                <form onSubmit={handleGitSubmit} className="space-y-8">
                                    <div className="grid md:grid-cols-2 gap-6">
                                        <div className="space-y-2">
                                            <Label htmlFor="git-url">Repository URL</Label>
                                            <div className="relative">
                                                <Github className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                                <Input
                                                    id="git-url"
                                                    placeholder="https://github.com/username/repo.git"
                                                    className="pl-9 h-10"
                                                    value={gitUrl}
                                                    onChange={(e) => setGitUrl(e.target.value)}
                                                />
                                            </div>
                                        </div>
                                        <div className="space-y-2">
                                            <Label htmlFor="git-branch">Branch</Label>
                                            <div className="relative">
                                                <GitBranch className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                                <Input
                                                    id="git-branch"
                                                    placeholder="main"
                                                    className="pl-9 h-10"
                                                    value={branch}
                                                    onChange={(e) => setBranch(e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="border-t pt-6">
                                        <TagInputs tags={gitTags} setTags={setGitTags} idPrefix="git" />
                                    </div>

                                    <div className="flex justify-end pt-4">
                                        <Button type="submit" size="lg" className="w-full md:w-auto min-w-[200px]" disabled={loading}>
                                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Start Import
                                        </Button>
                                    </div>
                                </form>
                            </TabsContent>

                            <TabsContent value="file" className="mt-0 space-y-6">
                                <div className="space-y-2 mb-6">
                                    <h2 className="text-2xl font-semibold">File Upload</h2>
                                    <p className="text-muted-foreground">Upload local files for immediate processing.</p>
                                </div>
                                <form onSubmit={handleFileSubmit} className="space-y-8">
                                    <div
                                        {...getRootProps()}
                                        className={`
                                            border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
                                            ${isDragActive ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/30'}
                                        `}
                                    >
                                        <input {...getInputProps()} />
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="p-4 rounded-full bg-background shadow-sm border">
                                                <Upload className="h-8 w-8 text-primary" />
                                            </div>
                                            <div className="space-y-2">
                                                <p className="text-lg font-medium">
                                                    {file ? file.name : "Click to browse or drag file here"}
                                                </p>
                                                <p className="text-sm text-muted-foreground">
                                                    PDF, Markdown (.md), Text (.txt), ZIP Archives
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="border-t pt-6">
                                        <TagInputs tags={fileTags} setTags={setFileTags} idPrefix="file" />
                                    </div>

                                    <div className="flex justify-end pt-4">
                                        <Button type="submit" size="lg" className="w-full md:w-auto min-w-[200px]" disabled={loading}>
                                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            {file ? 'Upload File' : 'Select File'}
                                        </Button>
                                    </div>
                                </form>
                            </TabsContent>
                        </div>
                    </Tabs>
                </div>
            </div>
        </div>
    );
};

export default InputPage;
