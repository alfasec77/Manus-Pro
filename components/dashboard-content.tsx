"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Terminal, FileText, Eye, ArrowDown, ArrowUp, Edit, Send } from "lucide-react"

interface DashboardContentProps {
  activeTask: string
  commandOutput: string[]
}

export function DashboardContent({ activeTask, commandOutput }: DashboardContentProps) {
  const [activities, setActivities] = useState([
    {
      id: 1,
      text: "Starting to extract and analyze resumes for RL algorithm engineer candidates.",
      command: "mkdir -p resumes && unzip -o upload/resumes_1_to_10.zip -d resumes",
      status: "completed",
      type: "command",
    },
    {
      id: 2,
      text: "Creating a todo list to track resume analysis progress.",
      status: "completed",
      type: "file",
      filename: "todo.md",
    },
    {
      id: 3,
      text: "Create candidate review task list",
      status: "completed",
      type: "task",
    },
    {
      id: 4,
      text: "Starting to read and analyze each resume, focusing on RL expertise and project experience.",
      status: "completed",
      type: "browse",
      path: "file:///home/ubuntu/resumes/resume_1.pdf",
    },
    {
      id: 5,
      text: "Read and analyze individual resumes",
      status: "in-progress",
      type: "task",
    },
    {
      id: 6,
      text: "Continuing to read and analyze resumes, focusing on RL expertise and project experience.",
      status: "in-progress",
      type: "view",
    },
    {
      id: 7,
      text: "Continuing to read and analyze resumes, troubleshooting PDF viewing issues.",
      status: "in-progress",
      type: "scroll",
    },
    {
      id: 8,
      text: "Analyzing resume content for candidate 1, focusing on RL-related experience.",
      status: "in-progress",
      type: "scroll-top",
    },
    {
      id: 9,
      text: "Analyzing resume content for candidate 1 (Amelia Martin), focusing on RL-related experience.",
      status: "in-progress",
      type: "file",
      filename: "candidate_profiles/amelia_martin.md",
    },
    {
      id: 10,
      text: "Continuing to analyze remaining resumes, focusing on RL expertise and project experience.",
      status: "in-progress",
      type: "edit",
      filename: "todo.md",
    },
    {
      id: 11,
      text: "Continuing to analyze remaining resumes, focusing on RL expertise and project experience.",
      status: "thinking",
      type: "thinking",
    },
  ])
  const [message, setMessage] = useState("")

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "command":
        return <Terminal className="h-4 w-4" />
      case "file":
        return <FileText className="h-4 w-4" />
      case "browse":
      case "view":
        return <Eye className="h-4 w-4" />
      case "scroll":
        return <ArrowDown className="h-4 w-4" />
      case "scroll-top":
        return <ArrowUp className="h-4 w-4" />
      case "edit":
        return <Edit className="h-4 w-4" />
      default:
        return null
    }
  }

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim()) {
      // Add user message to activities
      setActivities((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: message,
          status: "completed",
          type: "user-message",
        },
      ])
      setMessage("")
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b bg-white flex items-center justify-between">
        <h1 className="text-lg font-medium">{activeTask}</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <FileText className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activities.map((activity) => (
          <div key={activity.id} className="mb-6">
            <p className="text-sm text-gray-700 mb-2">{activity.text}</p>

            {activity.type === "command" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <Terminal className="h-4 w-4 text-gray-500" />
                <span>{activity.command}</span>
              </div>
            )}

            {activity.type === "file" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <FileText className="h-4 w-4 text-gray-500" />
                <span>Creating file {activity.filename}</span>
              </div>
            )}

            {activity.type === "browse" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <Eye className="h-4 w-4 text-gray-500" />
                <span>Browsing {activity.path}</span>
              </div>
            )}

            {activity.type === "view" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <Eye className="h-4 w-4 text-gray-500" />
                <span>Viewing the page</span>
              </div>
            )}

            {activity.type === "scroll" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <ArrowDown className="h-4 w-4 text-gray-500" />
                <span>Scrolling down</span>
              </div>
            )}

            {activity.type === "scroll-top" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <ArrowUp className="h-4 w-4 text-gray-500" />
                <span>Scrolling to top</span>
              </div>
            )}

            {activity.type === "edit" && (
              <div className="bg-gray-100 p-2 rounded text-xs font-mono flex items-center gap-2">
                <Edit className="h-4 w-4 text-gray-500" />
                <span>Editing file {activity.filename}</span>
              </div>
            )}

            {activity.type === "thinking" && (
              <div className="flex items-center gap-2 text-blue-500">
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <span>Thinking</span>
              </div>
            )}

            {activity.type === "user-message" && (
              <div className="bg-blue-50 p-2 rounded text-sm">
                <span>{activity.text}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="border-t p-4 bg-white">
        <form onSubmit={handleSendMessage} className="flex items-center gap-2">
          <Input
            placeholder="Message Manus"
            className="flex-1"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <Button type="submit" size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}

