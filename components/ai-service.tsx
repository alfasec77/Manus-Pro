"use client"

import { useState } from "react"
import { generateText } from "ai"
import { openai } from "@ai-sdk/openai"

interface AIServiceProps {
  prompt: string
  onResult: (result: string) => void
}

export function AIService({ prompt, onResult }: AIServiceProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateResponse = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const { text } = await generateText({
        model: openai("gpt-4o"),
        prompt: prompt,
        system: "You are Manus, an AI assistant that helps with productivity tasks.",
      })

      onResult(text)
    } catch (err) {
      setError("Failed to generate response. Please try again.")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div>
      {isLoading && <div className="text-sm text-blue-500">Thinking...</div>}
      {error && <div className="text-sm text-red-500">{error}</div>}
    </div>
  )
}

