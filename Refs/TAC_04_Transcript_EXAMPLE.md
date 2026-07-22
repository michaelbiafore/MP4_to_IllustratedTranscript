# Tactical Agentic Coding - Lesson 4: Stay Out of the Loop

## Table of Contents

- [Introduction](#introduction)
- [Two Types of Agentic Coding](#two-types-of-agentic-coding)
  - [In-Loop Agentic Coding](#in-loop-agentic-coding)
  - [Out-Loop Agentic Coding](#out-loop-agentic-coding)
- [Why Stay Out of the Loop](#why-stay-out-of-the-loop)
  - [Agentic Coding KPIs](#agentic-coding-kpis)
  - [Betting on the Future](#betting-on-the-future)
- [AI Developer Workflows (ADW)](#ai-developer-workflows-adw)
  - [What is an ADW](#what-is-an-adw)
  - [The Power of ADWs](#the-power-of-adws)
- [Four Elements of AFK Agents (PiTER)](#four-elements-of-afk-agents-piter)
  - [Prompt Input](#prompt-input)
  - [Trigger](#trigger)
  - [Environment](#environment)
  - [Review](#review)
- [Demo: Simple Chore Workflow](#demo-simple-chore-workflow)
  - [Creating the GitHub Issue](#creating-the-github-issue)
  - [Watching the Agent Work](#watching-the-agent-work)
  - [Reviewing the Pull Request](#reviewing-the-pull-request)
- [Setting Up Your Local Environment](#setting-up-your-local-environment)
  - [Cloning and Installation](#cloning-and-installation)
  - [Environment Variables](#environment-variables)
  - [Health Check](#health-check)
- [Demo: Feature Implementation (JSONL Support)](#demo-feature-implementation-jsonl-support)
  - [Creating the Feature Issue](#creating-the-feature-issue)
  - [Running the ADW](#running-the-adw)
- [Breaking Down the ADW Code Structure](#breaking-down-the-adw-code-structure)
  - [The Workflow Overview](#the-workflow-overview)
  - [Issue Classification](#issue-classification)
  - [Branch Creation](#branch-creation)
  - [Build Plan](#build-plan)
  - [Execute with Claude Code](#execute-with-claude-code)
- [Observability and Logging](#observability-and-logging)
- [Testing the Implemented Feature](#testing-the-implemented-feature)
- [Key Takeaways and Recommendations](#key-takeaways-and-recommendations)
  - [The Agentic Layer](#the-agentic-layer)
  - [Getting Started](#getting-started)
- [Preview: Lesson 5](#preview-lesson-5)

---

## Introduction

You step out of the loop and you let your product build itself. How is this possible? We do this by adding four elements of AFK agents. This enables you to trigger your agents to run in their own environment.

By the end of this lesson you'll know exactly how to replace and outperform modern cloud-based agentic coding tools like Copilot, Devin, Jules, Codex, and other in-the-cloud coding agents. These tools are great - I've used them all - but they lack the detail needed to ship end-to-end in your codebase with your engineering practices for your domain-specific problem. They all have natural limits because they're literally designed for everyone's codebases, not yours.

Just like the prompt, your agentic pipeline is too valuable to outsource to a third-party tool, especially this early in phase two of the generative AI age. You want to own your agentic pipelines. You want to be able to slice and dice your agents across your codebases, across the software developer lifecycle with ease.

In this lesson we put together the plan and build step of the software developer lifecycle to augment and automate your codebases. Every tactic you'll learn was created to be simple, compressed mental frameworks you can use every single day for your engineering work.

### Course Progression

1. First, you **stop coding** - our hands and mind are no longer the best tool for the job of writing code
2. Then you **adopt your agent's perspective** so you can maximize the leverage you get from your agents
3. Then you **template your engineering** so you can deliver consistent results in complex codebases across hundreds of agent executions
4. And now here in Lesson 4, you **stay out the loop**

---

## Two Types of Agentic Coding

What does it mean to stay out the loop? There are two types of agentic coding - both powerful, both relevant - but one lets you hand off exponentially more work to your agents.

### In-Loop Agentic Coding

You've of course heard of human-in-the-loop. When it comes to agentic coding, this is what most engineers are doing right now. The tech ecosystem has become obsessed with human-in-the-loop systems, and most fail to recognize the trend that there are increasingly more chores, bugs, and features that don't require your expertise at all if you encode them.

They're sitting on their device, in the loop, prompting back and forth and back and forth, burning their precious time on work that could be handed off to the right team of agents in the right order with the right templates. This is classical in-loop agentic coding.

### Out-Loop Agentic Coding

Out-loop agentic coding is off-device agentic coding. It's when you write high-to-low level prompts that you pass off to your agentic pipeline, then you go AFK (away from keyboard). You walk away from your keyboard, or maybe you were never there in the first place. Maybe you sent the prompt right from your phone on GitHub, Slack, Notion, Jira, a text message, or any third-party tool.

**Stay out the loop** is a tactic of agentic coding that reinforces the fact that models will improve and tools will change. This means over time your agents will be able to solve more and more problems with every improvement. When you stay out the loop, you leverage this fact, enabling you to focus on scaling up what your agents can do instead of wasting time doing the work yourself.

**You build the system that builds the system.** This is where we need to focus.

---

## Why Stay Out of the Loop

### Agentic Coding KPIs

Why is building the system that builds the system so important? It's because this directly ties into our ability to improve our agentic coding KPIs:

- **Presence**: Down
- **Size**: Up
- **Streak**: Up
- **Attempts**: Down

What's the best way to accomplish great agentic coding KPIs? You guessed it - stay out the loop and focus on building the system that builds the system.

We're going to accomplish this by adding a net new agentic layer to your codebases. This is going to be different, it's going to be a little challenging, and it's going to be incredible if you take action on this.

Here in Tactical Agentic Coding, we're obviously capitalizing on this opportunity before it hits the masses. We're not playing today's game - we're playing tomorrow's.

### Betting on the Future

You might be thinking about how error-prone LLMs and agents can be, or how AI can't possibly ship your special snowflake work end-to-end. Let me say this bluntly and clearly: **if you are not wrong now, you will be**. It's only a matter of time.

Remember: tools will change and models will improve. That means engineers, teams, leaders, and businesses betting on the future are the ones that will get ahead today. There's no way around this. Keep it simple and bet on the future. Lean into this.

You want to be the one shipping more features with less friction, with fewer errors, agentically, hands-off, AFK. This means you get to product-market fit faster and you expand your total addressable market faster. With every day, with every improvement you make to your templates and to your agents, your current velocity is fractions of what it will be when your agents are doing all the heavy lifting for you because you've learned to stay out the loop and build the system that builds the system.

---

## AI Developer Workflows (ADW)

Staying out the loop sounds great, but how does it actually work? And how can we differentiate from the plug-and-play out-loop agentic coding tools that already exist?

With everything you've learned so far here in TAC, we can automate nearly half the software development lifecycle and go from prompt to PR.

In Lesson 3, you learned to template your engineering. Investing in your templates is mission critical for out-loop agentic coding because when you template your engineering, you encode your engineering solutions into your codebases for your agents.

Notice how I keep stressing the uniqueness and the ownership of your codebase and your agents. As much as the big GenAI companies building these out-loop apps and tools want you to believe this, **one size does not fit all** - especially as your product grows and becomes unique and differentiated.

### What is an ADW

In this lesson, we chain your templates together inside the highest leverage point and the highest composition level of agentic coding: the **ADW (AI Developer Workflow)**.

An ADW is a reusable agentic workflow that combines code, agentic prompts, and agents to deliver results autonomously. On the battleground of agentic engineering, the ADW is how you create this new agentic layer around your codebase.

It's the synthesis of:
- Previous generation deterministic code
- New generation non-deterministic language models
- Prompt chains
- Agents

The ADW can be thought of as an agentic pipeline or, very loosely speaking, an agentic workflow. In the future, these will just be known as scripts, and we'll fully expect agentic behavior by default. We're creating a concrete term for this, pulling it from Principle Day Coding, to be absolutely clear about how powerful and differentiated this unit of engineering is.

### The Power of ADWs

AI Developer Workflows are what we'll use to automate not just the software developer lifecycle, but all engineering work and all workflows you want your agent to operate on your behalf.

If you understand this lesson and start putting these ideas to work in your codebase, you'll fast-track your transition into the future of agentic coding. While other engineers are sitting at their device prompting back and forth and back and forth, wasting time on problems their agents could solve, you'll have built a new agentic layer around your codebase where you stay out the loop and let your product build itself.

---

## Four Elements of AFK Agents (PiTER)

In order to build out-loop systems, we need AFK agents - agents that run while we're away from the keyboard. There are four elements of AFK agents we need to build our out-loop system. This is what we're going to focus on here in Lesson 4.

The four elements can be remembered with **PiTER**:

| Element | Description |
|---------|-------------|
| **P**rompt Input | The source of work requests |
| **T**rigger | What initiates the workflow |
| **E**nvironment | Where the agent runs |
| **R**eview | How you validate the output |

With this setup, your agents can run while you're AFK. AFK agents are the agents you'll build to run the loop while you stay out of it.

In this lesson, we'll run two ADWs to automate the plan and build steps of the software development lifecycle. We'll go from prompt input to review.

### Prompt Input

For our prompt input, we'll use GitHub Issues. Here we'll create new issues, and the title and description will be the prompt that our agent will execute on.

### Trigger

For our trigger, we're going to use GitHub webhooks. You can set up your own webhook, and all the information you need to set up your own workflow using these elements will be linked in your loop box.

I recommend you just watch to start and follow along at a high level. Don't get bogged down in the configuration of this - just watch this through first and then start setting up your four elements.

### Environment

For the environment, I'm going to use a Mac Mini that my agent has full control over. If we open up screen sharing, you can see I have an agent ready and waiting, looking for requests from the webhook right here.

This is our environment - we're looking into this device right here. When we kick off our prompt input, you're going to see this start up and boot up.

### Review

Our review system is going to be GitHub Pull Requests. After our agent finishes the work we've asked for with the prompt input, it's going to turn around, do the work in its environment, and then submit a pull request back for us to review.

---

## Demo: Simple Chore Workflow

Instead of diving right into the TAC 4 codebase, let's just look at how this simple out-loop system works end-to-end.

### Creating the GitHub Issue

Let's start with our prompt source: GitHub Issues for the TAC 4 codebase. I'm going to create a lightweight issue for us to understand this process:

**Title:** ADW Documentation

**Description:** `/chore` to document the ADW directory. Read everything in ADW then update README with information how it works.

Chores are the simplest unit of engineering work that your agents should be taking off your plate with no debate at all. So let's kick off this ADW and watch what happens inside of the agent environment.

### Watching the Agent Work

I'm going to create a brand new issue here, and check this out - right away your agent is getting to work for us.

If we click here, we can see we're getting GitHub issue comments. We're getting a live feed of the progress of our agent. You can see it's classified the issue as a **chore**. In our previous lesson, we looked at chores, bugs, and features. This is how we can specialize certain agents and certain prompts to solve different problems in your codebase.

So we have a brand new branch, and it's starting to work on the implementation plan. You can see the software developer lifecycle planner has taken over and it's going to start shipping. This is all running on this device here - it's posting comments and working through the current implementation plan.

This device, this agent, is doing this work autonomously for us. Not only that, we're getting a nice live feed of what's actually happening.

**By separating our agents, we're able to isolate the Big Three - context, model, and prompt - to solve one problem and solve one problem well.**

Just in these four steps, we have several micro-agents doing their work, solving a specific problem well:
1. A prompt to classify this work
2. Spinning up a new branch
3. An implementation plan
4. Our planner completing and committing its work

Our planner is completely done - it's committed its work right here. We can see that it's created a brand new spec file agentically. Now our implementer agent is going to start implementing the solution. Its context window is completely free. We can select a more powerful model (which I recommend you do for the implementation), and we can use the plan that was created by our planner as the prompt for our implementer.

You can see how all these elements - every piece of our ADW, our AI Developer Workflow - it all depends on the fundamental principles of AI coding and of agentic coding. These ideas, these concepts, they don't go anywhere - they go everywhere. These are ideas that will always exist and we need to pay attention to them with each prompt, with each agent.

**The details are everything.**

There's a reason why a lot of agentic coding tools don't work - it's because they don't understand your codebase. They don't understand how you work. And by encoding them into our templates and then chaining our templates, our meta prompts, and reusable prompts together, we get an ADW that can do work like this.

You can see the solution was implemented and now we're committing the implementation. Our agent, working on its own device here, is running through this ADW, this AI Developer Workflow. It's creating a PR. All this work is happening without us, but it's happening as if we were building it because we've templated our engineering.

**Success is absolutely planned. You can plan success into your codebase by templating your engineering.**

### Reviewing the Pull Request

Here comes the PR - there it is! ADW completed. If we scroll up, we can see how long that took. This simple task took a total of **five minutes**, and you can see our agents did all the work there. All we did was define the work that we want done and gave it a little bit of detail.

This is a high-level prompt that gets turned into a plan - it's expanded. Our agent is filling in the details of our chore, just like in the TAC 3 lesson. Our chore is getting expanded into a full plan, and then our implementer is building it out.

If we click this PR, you can see top to bottom a great clean write-up of the work completed. This PR addresses issue #31. You can see the plan there and then you can see the changes that were made.

If we scroll down, you can see everything looking good. And you know, there are issues here that I need to clean up, that I need to encode - we have "agentic developer workflow" that's just wrong. So this is something that I need to improve in my prompt to be clearer about what this is.

But you can see here, if we go to "Files changed," we can see just those files we asked for to be updated. There's the README - we can quickly scroll through this. We have changes for the README detailing exactly how everything works for the ADWs. There's the webhook that's running this workflow, cron, and then the build step and then the actual ADW.

There are no limits here - your ADWs can operate on your ADWs. So don't get too meta, let's keep it simple.

And then of course we have the plan. This plan was built by our planner agent and then handed off to our implementer agent. So this was literally the prompt for our implementer agent. You can see top to bottom there exactly what that looks like.

**This is awesome! This all happened with PiTER - the four elements of AFK agents:**
- For the prompt input, we used GitHub Issues
- For the trigger, we set up a GitHub webhook
- Our device picked up on that and ran our ADW, our Plan-Build AI Developer Workflow
- Then it submitted a PR back to our review system, and we reviewed the PR

Here we just have two steps of the software developer lifecycle fully automated end-to-end. I hope you can see how powerful this can be. Just halfway through TAC, we can automate the key steps of the software developer lifecycle. Obviously, we're going to take this a lot further, we're going to push this.

---

## Setting Up Your Local Environment

Now let's dive into the details of how this works so that we can see the ADWs are in fact a composition of key primitives that we can work with to build an agentic layer around any codebase you operate in.

Keep in mind as we work through this that these four elements can be anything. I'm not here to tell you what tools or what environments to use, what sandboxes to put your agents in. I'm here to give you a top-notch framework and tactics you need so that you can build the system that works for your codebases, your products, and your team.

You will and you should have opinions about how to structure your AFK agents. Don't read into how this is configured too much - focus on the composable units.

### Cloning and Installation

Let's run this again, only this time I'm going to update so that our environment is my local device and my trigger will be a local script we'll run right out of the TAC 4 codebase.

```bash
ls
# You can see we have the previous three TAC codebases

git clone [lesson 4 repository]
cd tac4
code .  # Open in VS Code
```

Let's boot up Claude. I'm going to run in "yellow mode" because I understand everything this codebase will and can do. If you're ever worried about the permissions, always check the settings file and make sure that things can't run that you don't want run. This is going to add additional control.

There's no reason to run installation by hand anymore, so I'm going to run `/install` and let's get this codebase set up.

Whenever you run these commands in new codebases, always check out what is actually inside the file. You can see here we've added a little bit more to this install command for this codebase. We're reading and executing, running several steps:

1. We need to unset the remote origin here
2. Set up a new GitHub repo so that you can use your own GitHub issues and PRs (you can't make PRs to this codebase - it needs to be reusable)
3. Copying our environment variables - we have a new top-level environment variable file we need to set up
4. Installation of frontend and backend dependencies as before
5. Copying our previous codebase `.env` file for our server

A cool thing you can add into your prompts is a **report feature**. It's going to set up some things, run all these previous commands, and then our agent is going to report some results to us - to the engineer, to your co-workers executing this script. It's going to have some useful information like "work completed" and "action required."

So it's telling me I need to fill out the root level `.env` and app level was already copied from TAC 2, and the API keys are all good there. To set up our AFK agent, we need to set up a remote repo so that we can get access to issues and PRs to satisfy the prompt input and the review system elements of AFK agents.

### Environment Variables

In the `.env` file, the key things you need are these two:

1. **ANTHROPIC_API_KEY** - The Agent SDK currently only runs with the API key. This may change in the future - keep your eye out for that.

2. **CLAUDE_CODE_PATH** - Depending on your configuration, this might not work right away. You need to run something like `which claude` and paste this in your environment variable.

### Health Check

Before we dive into running the ADW, let's create a prompt input for this workflow to run on this device. Open up GitHub Issues, hit "New Issue," and let's have our agent build out a new feature for us.

But first, let's validate our environment by running this health check command. This is something I highly recommend you build into your ADWs. Before you run your complex or simplistic workflow, you just want to know that everything's configured properly.

```bash
# Run the health check on issue 33
uv run adw/health_check.py 33
```

These are all single-file scripts by the way. The ADW directory is really important because it operates as a unit around your codebase. Notice how `app` is completely untouched here - we're not combining or conflating the functionality between these two.

The ADWs combined with your prompts (as you'll see in a moment - you can see all these reusable prompts that fuel the ADWs) - these two directories and their content form the **agentic layer** around your codebase.

So let's run the health check on issue 33 and see if we have everything set up properly:
- Environment path is set up
- GitHub repository looks good
- We do get a warning if you're still pointing toward the original TAC 4 lesson codebase
- Claude Code runs properly
- We posted a health check onto the comment

We are good to go! We're good to run our AI Developer Workflow.

---

## Demo: Feature Implementation (JSONL Support)

### Creating the Feature Issue

Let me quickly refresh our memory on this codebase. We can execute it with:

```bash
sh script/start
```

This kicks off our backend and frontend. We have our classic natural language interface - we can upload test data, we can get users, we can query these users ("users age descending"), and that query will come through as an SQL statement against our local SQLite database. It all looks good.

What we want to do here in this new feature: we're going to add **JSONL support**. If we hit upload, you can see right now we can only do `.csv` or `.json`.

Let's kick off this ADW. The first thing we need to do is write the prompt input - this is step one of the four elements of out-loop systems, of AFK agents.

**Issue Title:** JSONL Support

**Issue Description:** Adding support for uploading JSONL files
- Standard lib only, no new libraries
- Handle nested fields, handle arrays
- Update the UI

This is a high-to-mid-level prompt where we detail what we want done. Brand new feature coming in - net new.

We have disabled our agent running in its own sandbox here (the webhook event is off, it's not listening), so this won't run. We're going to kick this off on our device with a local trigger.

### Running the ADW

Let's create this issue and reference it by pulling number 33. If we open up the top of our ADW plan-build, we only have one ADW in this codebase - just the plan and the build. Remember, we're automating the plan and build step of the software developer lifecycle.

```bash
# Run the ADW
uv run adw/plan_build.py 33
```

These scripts - these single-file scripts - can be anything you want. Using Astral UV to run Python single-file scripts. You can see you have a couple of dependencies there. These can be Bun scripts if you want, shell scripts, whatever you want. The whole point is that they're a layer on top of your codebase.

And here we go! Just like in our environment, it's running that exact same workflow now. The only difference is I kicked this off with a manual trigger. It has its own unique ADW ID to identify this AI Developer Workflow. And now it's got its own branch: `jsonl-support`.

Now it's going to do this work for us agentically. You can see the branch that we're operating on in this codebase just got updated. Our agent has taken the wheel. We are now **out of the loop**.

We said what we want done, and now it's starting to do the work for us. We're focusing on the **what**, not the **how**. The details of how things are done, we've already encoded into our codebase via our reusable prompts, our templates, and our meta prompts.

If we hop back to the issue, you can see our agent is updating this live, just like our previous. The issue has been classified as a **feature**. So instead of running the chore, it's going to run the feature here. This feature template meta prompt is going to build out an entirely different set of instructions and a different template for our agent to fill out and operate on.

We can target specific classes of problems with this switch - with this feature inside of our ADW that classifies: is this a chore, bug, feature, or any other specific class of problems that you solve in your codebase? This is a very important pattern of agentic coding - you need to be able to target specific classes of problems.

---

## Breaking Down the ADW Code Structure

While our agent's building this out on our device, let's go ahead and break down how exactly this works inside of the codebase. How is our agent doing this work for us agentically?

### The Workflow Overview

It all starts in the ADW plan-build. Here's the workflow - it's right here at the top of the file. Very easy to understand:

1. **Fetch the GitHub issue details** - Pull in the prompt source
2. **Create a feature branch** for this work (could be a chore or bug as well)
3. **Run our plan agent** - There's going to be code with a specific plan prompt. It's going to run our `/feature` reusable prompt
4. **Build agent takes the plan** - Based on the plan, it'll pull in all the right context. Again, we did this in our previous lesson with the `/implement` command. We're going to pass the plan in as an argument and then it executes
5. **Create a PR**

So right here, we're automating the first two steps of the software developer lifecycle: plan and build, plan and code, with this ADW.

Let's break this down. You can see here at the top, we have different agents for different specific tasks. What's important right now is that you understand that you can put together these composable units of classic deterministic code with these new units of intelligence with our Claude Code agentic coding agent. It's all about that.

And then **reporting** - making sure that our process is observable and understandable from a higher level. It doesn't matter if our agent can solve every problem if we don't know that it's solved. We need to observe, we need to report, we need to log and monitor.

What we have here in this ADW is exactly that. We're putting together these elements, these composable units of agentic engineering, and we're letting the product build itself with this new agentic layer around the codebase.

Let's walk through this - it's relatively simple:

1. Parse the arguments, pass in the issue number (you can see issue number 33 right here)
2. If we don't have an ADW ID passed in (this is optional), we make one
3. Setting up our logger
4. Checking the environment variables
5. Getting our GitHub repo

We have different modules we're pulling in: data types, GitHub, and agent.

Then we fetch the issue from GitHub. This is going to pull in title and description so that we have the actual issue. We can see this type very plainly here - we've just got this all typed out. The key thing here is the `title` and `body`.

And then we have this pattern of either reporting the issue (you can see all the issue comments here - by "issue" I mean the issue comment, so we're adding a comment on the GitHub issue) or we are checking the error.

In between all of our logging and reporting, we're just running the individual steps of our ADW.

### Issue Classification

Here's that `classify_issue`. Check this out - this is our prompt that we're running as a slash command. We're going step by step, isolating all of our prompts so that we can improve them. **No ad hoc prompts as strings inside of the codebase** - everything is isolated so that we can improve it.

We have a nice mapping here. Of course, if you have more detailed or different classes of problems, you just add them here in your `classify_issue` step, and then you update your data types to support the different types of slash commands that you solve.

Again, this is just one way to build out an ADW. We're just walking through this so you can understand how you can build these out for your codebase, for your problem, for your application, for your team, for your users.

### Branch Creation

We then create a git branch, and again it's the same process. `git_branch` is created by our `branch_pr`. Notice how with every one of these templates, we're encoding our engineering into reusable prompts that our agent can tap into.

This is all about that same idea, that same tactic: we need to **adopt our agent's perspective**. Behind that, we need to **give our agent our perspective**. They need to see what we would see when we're solving that specific step of the AI Developer Workflow.

Because previously these are just developer workflows - this is what you and I are doing on the ground every day. But now we can add this new agentic layer and then we can augment and automate a lot of these processes.

### Build Plan

Let's go into `build_plan` and let me show you what one of these methods actually looks like. We're building a template request:

- **Agent name**
- **Slash command** - Remember, the slash command activates the right prompt
- **Arguments** that go into the prompt
- **Specifying the model**

When you run this and when you set up your ADWs, I highly recommend for your build and implement steps - your build and implement - you use the most powerful model you can. Just for presentation sake, I'm using Sonnet because it's going to be a little faster, but you're going to want to throw top models into the most complex steps, which are going to be your plan and your build step.

`build_plan` - we're just going to kick off this slash command, run some debugging logs, and we're going to execute it.

### Execute with Claude Code

All the way at the bottom here, the execute step is of course in our agent module, which is going to:
1. Build the prompt
2. Log the prompt
3. Run the code using **Claude Code in programmable mode**

This is why this is so important - we're kicking off Claude Code right here. Be sure to read through this. It is running dangerously, but because it's in its own environment, this is going to be safe.

The key idea here is this is the value of **programmable mode**. This is why it's so powerful - it lets us use Claude Code as a new agentic coding primitive where we can call our agent with any prompt and any step of our workflow that we need to automate engineering work.

This is all here - this is going to set up a great base framework for you to understand ADWs and build them into your own codebases. This is going to call the build prompt, call the right slash command with the planner agent. After that, we just continue the flow, tab into whatever next step we want.

If we scroll down from here, we're checking errors, continuously updating on what the issue is, on what's coming next, and we're making it observable.

---

## Observability and Logging

A couple really key pieces here that we're going to look at in upcoming lessons:

We have our system reporting individual log files on a **Claude Code session ID basis**, so we can come into this system, this device, and really understand what's going on here at a very, very detailed level. We activated this thanks to Claude Code hooks, but there are many mechanisms to tap into this functionality. That's one mechanism in which we can observe and review.

We also have agents that run on an AI Developer Workflow basis. This workflow has completed, and you can see all the agents - all the little micro-to-macro agents inside this ADW that have completed:
- Branch generator
- Issue classifier
- PR creator
- Implementer
- Planner
- Committer for the planner
- Committer for the implementer

You can see that if we continue to scroll down, it's all the same process: run either non-deterministic intelligence or a deterministic step, then check for issues, do some logging, do some reporting, and then continue. Now we're committing the plan. There's a git commit. Then we're implementing the solution - there it is, plan file. On and on - there's the git commit for the implementation. Then we're building out the pull request.

This is our PR creator. If we tap this, we can see all the logs that our PR creator went through. We have JSON-L here and JSON for more easy readable format.

This is how this ADW works. We'll dive into the details and play with these composable units as you progress through each lesson. But this is important: **ADWs let us create a new agentic layer around our codebase that tells our agents how to operate and perform real engineering work.**

---

## Testing the Implemented Feature

If we look here, this workflow is complete. There's the PR. We can get out of this. Look at this issue here - you can see this entire workflow took about **17 or so minutes**. And there it is.

We now have JSONL support! We can hop in here, review this. There's all the files changed, all getting reported based on our PR review prompt. This looks great - it handles all these key features, comprehensive test coverage, love to see that.

And then we can of course review all this code, see the files changed, see everything that's changed. There's the frontend UI updated. Here is some sample data just like we asked for in our test - complex data, sample data, and on and on.

And of course, very importantly, here's the **plan**. The planner created the plan and outputted a concrete asset that we can use to understand what our implementer will do. This is really, really important. This lets you improve.

It's not enough to just run a random ad hoc prompt because how will you know how to improve that? And more importantly, how will your agents know how to improve that? We can look through this entire plan - you can see it's very comprehensive. Our agent created a **170-line plan**, and then our implementer went and built this out.

So we have an opinionated plan-build workflow that fits our codebase for building features.

### Verifying the Feature Works

Let's hop into this codebase and see how this actually turned out. Because our agent was updating in this environment, you can see we're still on that feature. So what I'll do here is just boot up the client and server again with all this updated code, and then let's just see what it looks like.

Let's open up Chrome, go to our natural language interface and refresh. You can see it's added a couple different test items (it was operating right on this SQL database). So that looks good - there are things there.

Let's do a quick regression test: `SELECT users descending sign update`, fire that off. We should get our same prompt - there we go. Nothing different there, ordered by descending. Looks great.

And now let's go ahead and try to upload some. Check this out - our UI got updated: **CSV, JSON, or JSONL**. That looks great! We have a new option. We can select event analytics. Looks good.

Let's drag and drop the sample data. On that PR it told us where exactly that was. Let's drag and drop in that sample data - this is going to be in test assets. So we can quickly find that: `app/server/tests/assets`. Let's open in Finder. Assets. Here we go.

Drag and drop simple JSON data here. You want to make sure this is a fresh upload. Upload sample data JSONL, drag and drop. There it is! Sample data from a JSONL file. And you can see we have that exact same naming convention as specified.

**This was a feature that an engineer may have taken up, may have picked up themselves, and it was completely unnecessary.**

I can guarantee you right now, you or an engineer on your team - you're working on things you can fully automate by creating an agentic layer around your codebase that is driven by the four elements of AFK agents. And doing all this will help you stay out the loop.

There's no reason to do engineering work like this, and this trend will continue. This is not specific to this codebase. Yes, right now it is small, but it doesn't matter - the size only matters so much.

And every time you miss something, what do you do? **You don't fix the issue - you fix the system that caused the issue.** You fix your templates. You fix your ADW.

Let's finish testing this: `sample data all rows age between 10 and 50`. Just a random query to showcase that all of our data is here. This feature was created in one shot. We now have JSONL support. That was created on this branch, on this machine. We set up the four elements and this happened end-to-end.

---

## Key Takeaways and Recommendations

I just want to stress this one more time: **it doesn't matter if you use GitHub Issues**. If you like Jira tasks, Notion boards, whatever you want to use - the key is that these four elements are always there, and you want to build systems that build the system for you. That's the key here. That's the key piece of information from this lesson.

### The Agentic Layer

Before we push this to the next level, let me touch on a couple things. We set up a GitHub webhook here and then I exposed this functionality via a proxy server (I'm using Cloudflare - you can use anything you want, set up your own dev infrastructure). The key is just to set up a **dedicated environment**.

I highly, highly recommend you do this. You want a dedicated environment that your agent can run in on its own. This way you can create a GitHub issue anywhere you want, or you can fire off a prompt input that hits a trigger that then kicks off your agentic workflows no matter where they're running.

This is super key, super important. We have two units of engineering work that happened agentically for our codebase - for the TAC 4 codebase. That's the key: **ADWs and the prompt templates you build out for your codebase - they solve classes of problems that you no longer have to solve.**

You don't immediately start with top-tier agentic coding KPIs. You're going to run some of these, you're going to run some ADWs, you're going to run some prompts, some templates that don't fully solve the problem. Then you'll spend some time, you'll invest in your templates, and then you'll compose them into your ADWs and you'll improve.

This is the new layer, the compositional unit that I highly recommend that you focus on now. Don't sit and prompt back and forth - build up these workflows. Your agent can solve many, many problems that you and others are still wasting your time building.

I want to be really blunt here - I want to help you get ahead, and that means addressing the faults of where we currently are.

In-loop agentic coding is great for:
- Experimentation
- Exploring new territory
- Very, very hard, very specific problems

But let's be real - **most of engineering is not that**.

So if you invest a little bit of time here setting up your reusable prompts - your templates, your meta prompts - and then creating some ADWs... once you set these up, they're just there. For this codebase, this just solves entire classes of engineering problems now, moving forward. These types of problems are just solved. All I have to do is write the prompt - the high-level prompt, not even the plan.

I hope you can see things coming together here. There's a lot to dissect, but the idea here is simple: **build a new agentic layer in your codebase so your agents can run and ship engineering work based on your engineering problems, based on your codebase.**

By doing this, by dedicating and focusing really hard on these two essential directories:
1. `.claude/commands` (aka wherever your prompts are stored)
2. `adws` (also known as compositional workflows - your agentic workflows, your agentic pipelines, your ADWs, AI Developer Workflows - so many names for the same thing)

You want to focus on these elements and create this outer layer to automate the different classes of software engineering problems that you have. Make sure you add logging, add observability. You want to make it easy to understand where and how things are happening.

We can hop into the issue and see this agent completed its work, then we can review to make sure that it is actually done. You want to set up the four elements of AFK agents: Prompt Input, Trigger, Environment, Review System.

This enables you - when you put these things together, you can stay out the loop.

### Getting Started

For example, this is one workflow, one out-loop system I have set up. This device now is always running for me. If I hop into this box and kick this trigger off again, this codebase is always listening to whatever webhook I have set up for any codebase now, and it will just start solving the problem.

After the upfront install (and you can encode all the installation into a `/install` command), after you get the setup, you have an agent operating in its own environment you can call using an out-loop system. This is **massive impact**.

I recommend you take action on this now. Don't wait - the ROI here is insane. I want you to get to the "aha lightbulb moment" you'll get when you run one of these end-to-end.

**Start with something simple:**
1. Get everything configured and fire off a chore
2. What you want to do is understand how controllable this is

Yes, it's true there are cloud-based tools that do this workflow, but that's not exactly true. These tools are not running your templates. They're not running your prompts. They're not built to solve your problems - your classes of problems that every engineer faces.

So invest in this. This is a critical, critical lesson.

**Start with great defaults:**
- For your prompt input: I highly recommend you just go with GitHub Issues
- For your review system at the end: GitHub PRs
- For your trigger and your environment: Just start setting this up locally and then offload it to another device

You want to get to this point where you start with low-hanging fruit. Build up trust in your ADW and your system that you're building.

1. **Start templating out the chore** for your codebase
2. **Then move up to bugs**
3. **Eventually you'll get to the feature level**

But you can definitely start small with just the chore. These are simple tasks you can hand off, then move to bugs, and then full-on features.

Use this codebase as a great starting point for understanding how you can build ADWs in your codebase. There's engineering work that you just truly don't need to do anymore. **Template your engineering and stay out the loop.** Focus on this new agentic layer, this new outer layer on your codebase, so that your product ships itself.

---

## Preview: Lesson 5

We now have a tactic that guides us toward building autonomous systems. When you stay out the loop:
- You prioritize agentic coding
- We solve problem classes
- We build a system that builds a system

Our systems - this agentic layer - is solving the detailed problems while we're teaching it how to. In a lot of ways, we're automating the central units of the software developer lifecycle so that we can focus on what we want: **the planning and the reviewing**.

By templating your engineering, we increase our planning velocity by encoding solutions to classes of problems into the outer layer of our codebase - the agentic layer.

This is great, but there is a massive issue. These workflows, although powerful, they require lots and lots of reviewing. At some level, we'll always need to review, but wouldn't it be great if we could increase our review velocity as we scale our planning and building velocity with our agents?

**In the next lesson, we're going to do exactly that.** We're going to close the loops. We're going to give our agents multiple leverage points of agentic coding needed to validate their own work. We're going to teach them how to do this on multiple dimensions. Because what's better than one test? Yes - two, three, or ten.

In Lesson 5, we teach our agents how to test and validate - not just backend work, not just scripts, but frontend and all types of engineering. By doing this, we increase our review velocity by teaching our agents how to validate their work.

**Great job here! You're making a ton of progress. You are halfway through Tactical Agentic Coding.**

Take some time to digest this information. There's a lot here. This lesson is pivotal. Your ability to internalize Lesson 3 and Lesson 4 will decide if you come out on top here.

**Template and stay out the loop.**

I'll see you in Lesson 5, where we increase the reliability of your agents by drastically cutting down the time you and your team need to spend reviewing and fixing agent outputs.

I'll see you in Lesson 5.
