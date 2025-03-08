"use client"

import type React from "react"

import { useState } from "react"
import { DashboardContent } from "@/components/dashboard-content"
import { ComputerView } from "@/components/computer-view"
import { Terminal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export default function DashboardPage() {
  const [activeTask, setActiveTask] = useState("Ranking Candidates for Reinforcement Learning Engineer Role")
  const [commandOutput, setCommandOutput] = useState<string[]>([])
  const [command, setCommand] = useState("")
  const [showTerminal, setShowTerminal] = useState(false)
  const [currentFile, setCurrentFile] = useState("todo.md")
  const [fileContent, setFileContent] = useState(`# Resume Analysis for RL Algorithm Engineer Candidates

## Extraction and Setup
- [x] Extract resumes from zip file
- [x] Create todo list

## Resume Analysis
- [x] Read and analyze resume_1.pdf
- [ ] Read and analyze resume_2.pdf
- [ ] Read and analyze resume_3.pdf
- [ ] Read and analyze resume_4.pdf
- [ ] Read and analyze resume_5.pdf
- [ ] Read and analyze resume_6.pdf
- [ ] Read and analyze resume_7.pdf
- [ ] Read and analyze resume_8.pdf
- [ ] Read and analyze resume_9.pdf
- [ ] Read and analyze resume_10.pdf

## Candidate Evaluation
- [ ] Create detailed profiles for each candidate
- [ ] Evaluate RL expertise for each candidate
- [ ] Rank candidates based on RL expertise

## Final Report
- [ ] Compile final report with rankings
- [ ] Present results to user`)

  const executeCommand = (cmd: string) => {
    // Simulate command execution
    setCommandOutput((prev) => [...prev, `$ ${cmd}`, "Command executed successfully"])
  }

  const handleCommandSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (command.trim()) {
      executeCommand(command)
      setCommand("")
    }
  }

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      <div className="flex-1 flex overflow-hidden relative">
        {/* Terminal toggle button */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowTerminal(!showTerminal)}
          className="absolute top-2 right-2 z-10"
        >
          <Terminal className="h-4 w-4" />
        </Button>

        {/* Terminal overlay */}
        {showTerminal && (
          <div className="absolute top-10 right-2 w-96 z-10 bg-black border border-gray-700 rounded-md shadow-lg overflow-hidden">
            <div className="flex justify-between items-center p-2 border-b border-gray-700">
              <span className="text-xs text-green-400 font-mono">Terminal</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTerminal(false)}
                className="h-6 w-6 p-0 text-gray-400 hover:text-white"
              >
                ×
              </Button>
            </div>
            <div className="text-green-400 text-xs font-mono h-64 overflow-y-auto p-2">
              {commandOutput.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
            <form onSubmit={handleCommandSubmit} className="flex p-2 border-t border-gray-700">
              <Input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                placeholder="$ Enter command..."
                className="text-xs h-8 bg-black text-green-400 border-gray-700"
              />
              <Button type="submit" size="sm" className="ml-1 h-8">
                Run
              </Button>
            </form>
          </div>
        )}

        {/* Main content */}
        <div className="w-1/2 h-full overflow-hidden">
          <DashboardContent activeTask={activeTask} commandOutput={commandOutput} />
        </div>

        {/* Computer view */}
        <div className="w-1/2 h-full border-l overflow-hidden">
          <ComputerView currentFile={currentFile} fileContent={fileContent} setFileContent={setFileContent} />
        </div>
      </div>
    </div>
  )
}

