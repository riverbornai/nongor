<template>
  <div
    class="h-screen bg-bg text-text selection:bg-primary/30 p-4 flex flex-col overflow-hidden font-sans"
  >
    <div class="mb-6 flex flex-col gap-2 relative z-10 shrink-0">
      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <!-- Riverborn Styled Rounded Logo Square -->
          <div class="w-8 h-8 flex items-center justify-center shrink-0">
            <img
              src="~/assets/static/logo.png"
              alt="Riverborn Logo"
              class="w-5 h-5 object-contain"
            />
          </div>
          <h2
            class="text-[22px] font-schibsted font-semibold tracking-tight text-primary"
          >
            Nongor
          </h2>
        </div>
        <div class="flex items-center gap-4">
          <!-- Switchers Group -->
          <div
            class="hidden md:flex items-center gap-6 h-11 bg-white/95 border border-primary/15 backdrop-blur-md rounded-xl px-5 shadow-none font-sans"
          >
            <!-- Embedding service switcher -->
            <div
              class="flex items-center gap-3 border-r border-primary/10 pr-6 h-full"
            >
              <span
                class="text-[10px] font-extrabold uppercase tracking-widest text-primary/70"
                >Embedding:</span
              >
              <div class="flex gap-1.5 text-[11px] uppercase font-extrabold">
                <button
                  @click="setEmbeddingService('local')"
                  :disabled="loading || uploading"
                  :class="
                    embeddingService === 'local'
                      ? 'bg-primary text-surface shadow-md shadow-primary/10'
                      : 'text-primary/70 hover:text-primary hover:bg-primary/5 disabled:opacity-30'
                  "
                  class="px-3.5 py-1.5 rounded-lg transition-all duration-300 active:scale-95 font-bold"
                >
                  Local
                </button>
                <button
                  @click="setEmbeddingService('openai')"
                  :disabled="loading || uploading"
                  :class="
                    embeddingService === 'openai'
                      ? 'bg-primary text-surface shadow-md shadow-primary/10'
                      : 'text-primary/70 hover:text-primary hover:bg-primary/5 disabled:opacity-30'
                  "
                  class="px-3.5 py-1.5 rounded-lg transition-all duration-300 active:scale-95 font-bold"
                >
                  OpenAI
                </button>
              </div>
            </div>

            <!-- Reranker service switcher (Auto-managed based on Embedding) -->
            <div class="flex items-center gap-3">
              <span
                class="text-[10px] font-extrabold uppercase tracking-widest text-primary/70"
                >Reranker:</span
              >
              <div class="flex gap-2 text-[11px] uppercase font-extrabold">
                <span
                  :class="
                    rerankerService === 'bge'
                      ? 'bg-primary/10 text-primary border border-primary/25 font-black'
                      : 'text-primary/45 border border-primary/10 bg-primary/[0.02]'
                  "
                  class="px-3 py-1.5 rounded-lg transition-all duration-300 select-none flex items-center gap-1.5 border font-bold"
                >
                  <svg
                    v-if="rerankerService === 'bge'"
                    xmlns="http://www.w3.org/2000/svg"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="text-primary"
                  >
                    <rect
                      x="3"
                      y="11"
                      width="18"
                      height="11"
                      rx="2"
                      ry="2"
                    ></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                  </svg>
                  Local (BGE)
                </span>
                <span
                  :class="
                    rerankerService === 'openai'
                      ? 'bg-primary/10 text-primary border border-primary/25 font-black'
                      : 'text-primary/45 border border-primary/10 bg-primary/[0.02]'
                  "
                  class="px-3 py-1.5 rounded-lg transition-all duration-300 select-none flex items-center gap-1.5 border font-bold"
                >
                  <svg
                    v-if="rerankerService === 'openai'"
                    xmlns="http://www.w3.org/2000/svg"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="text-primary"
                  >
                    <rect
                      x="3"
                      y="11"
                      width="18"
                      height="11"
                      rx="2"
                      ry="2"
                    ></rect>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                  </svg>
                  OpenAI
                </span>
              </div>
            </div>
          </div>

          <!-- Settings toggle button for mobile/tablet -->
          <button
            @click="showSettings = !showSettings"
            :class="
              showSettings
                ? 'bg-primary text-surface border-transparent'
                : 'text-primary/70 hover:text-primary hover:bg-primary/5 border-primary/15 bg-white/95'
            "
            class="md:hidden w-11 h-11 border backdrop-blur-md rounded-xl flex items-center justify-center transition-all duration-300 active:scale-95 shadow-none"
            type="button"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path
                d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
              />
            </svg>
          </button>

          <div
            class="flex items-center gap-2.5 h-11 bg-white/95 border border-primary/15 backdrop-blur-md rounded-xl px-4 shadow-none font-sans"
          >
            <span
              class="flex h-2.5 w-2.5 rounded-full bg-primary animate-pulse"
            ></span>
            <span
              class="text-[10px] font-extrabold text-primary uppercase tracking-widest hidden sm:inline"
              >System Ready</span
            >
          </div>
        </div>
      </div>

      <!-- Collapsible Mobile Settings Panel -->
      <div
        v-if="showSettings"
        class="md:hidden border border-primary/15 rounded-xl bg-white/95 backdrop-blur-md p-4 mt-2 flex flex-col gap-4 animate-in slide-in-from-top-2 duration-300 font-sans shadow-none"
      >
        <!-- Embedding service switcher -->
        <div class="flex flex-col gap-2">
          <span
            class="text-[10px] font-extrabold uppercase tracking-widest text-primary/70"
            >Embedding:</span
          >
          <div class="flex gap-1.5 text-[11px] uppercase font-extrabold w-full">
            <button
              @click="setEmbeddingService('local')"
              :disabled="loading || uploading"
              :class="
                embeddingService === 'local'
                  ? 'bg-primary text-surface shadow-md shadow-primary/10'
                  : 'text-primary/70 hover:text-primary hover:bg-primary/5 disabled:opacity-30'
              "
              class="flex-1 px-3.5 py-1.5 rounded-lg transition-all duration-300 active:scale-95 font-bold"
            >
              Local
            </button>
            <button
              @click="setEmbeddingService('openai')"
              :disabled="loading || uploading"
              :class="
                embeddingService === 'openai'
                  ? 'bg-primary text-surface shadow-md shadow-primary/10'
                  : 'text-primary/70 hover:text-primary hover:bg-primary/5 disabled:opacity-30'
              "
              class="flex-1 px-3.5 py-1.5 rounded-lg transition-all duration-300 active:scale-95 font-bold"
            >
              OpenAI
            </button>
          </div>
        </div>

        <!-- Reranker service switcher -->
        <div class="flex flex-col gap-2">
          <span
            class="text-[10px] font-extrabold uppercase tracking-widest text-primary/70"
            >Reranker:</span
          >
          <div class="flex gap-2 text-[11px] uppercase font-extrabold w-full">
            <span
              :class="
                rerankerService === 'bge'
                  ? 'bg-primary/10 text-primary border border-primary/25 font-black'
                  : 'text-primary/45 border border-primary/10 bg-primary/[0.02]'
              "
              class="flex-1 px-3 py-1.5 rounded-lg transition-all duration-300 select-none flex items-center justify-center gap-1.5 border font-bold"
            >
              <svg
                v-if="rerankerService === 'bge'"
                xmlns="http://www.w3.org/2000/svg"
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-primary"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              Local (BGE)
            </span>
            <span
              :class="
                rerankerService === 'openai'
                  ? 'bg-primary/10 text-primary border border-primary/25 font-black'
                  : 'text-primary/45 border border-primary/10 bg-primary/[0.02]'
              "
              class="flex-1 px-3 py-1.5 rounded-lg transition-all duration-300 select-none flex items-center justify-center gap-1.5 border font-bold"
            >
              <svg
                v-if="rerankerService === 'openai'"
                xmlns="http://www.w3.org/2000/svg"
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-primary"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
              OpenAI
            </span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <p
          class="text-[10px] font-bold text-text-muted uppercase tracking-[0.2em] opacity-40 whitespace-nowrap"
        >
          Querying Private Knowledge Base
        </p>
        <div
          class="h-[1px] flex-1 bg-gradient-to-r from-border/50 to-transparent"
        ></div>
      </div>
    </div>

    <!-- Mobile Tabs (visible only on mobile/tablet) -->
    <div
      class="lg:hidden flex border border-primary/10 rounded-xl bg-white/80 backdrop-blur-md p-1 mb-4 gap-1 shrink-0 z-10 font-sans"
    >
      <button
        @click="activeTab = 'chat'"
        :class="
          activeTab === 'chat'
            ? 'bg-primary text-surface shadow-sm font-black'
            : 'text-primary/70 hover:text-primary font-bold hover:bg-primary/5'
        "
        class="flex-1 py-2 px-3 rounded-lg text-[10px] uppercase tracking-widest transition-all text-center flex items-center justify-center gap-1.5"
        type="button"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path
            d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
          />
        </svg>
        Chat
      </button>
      <button
        @click="activeTab = 'upload'"
        :class="
          activeTab === 'upload'
            ? 'bg-primary text-surface shadow-sm font-black'
            : 'text-primary/70 hover:text-primary font-bold hover:bg-primary/5'
        "
        class="flex-1 py-2 px-3 rounded-lg text-[10px] uppercase tracking-widest transition-all text-center flex items-center justify-center gap-1.5"
        type="button"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        Upload
      </button>
      <button
        @click="activeTab = 'sources'"
        :class="
          activeTab === 'sources'
            ? 'bg-primary text-surface shadow-sm font-black'
            : 'text-primary/70 hover:text-primary font-bold hover:bg-primary/5'
        "
        class="flex-1 py-2 px-3 rounded-lg text-[10px] uppercase tracking-widest transition-all text-center flex items-center justify-center gap-1.5"
        type="button"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path
            d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
          />
        </svg>
        Sources
      </button>
    </div>

    <div class="flex-1 flex flex-col lg:flex-row gap-4 overflow-hidden">
      <div
        class="flex-col gap-4 h-full lg:w-[450px] lg:shrink-0 lg:flex"
        :class="{
          'flex w-full': activeTab === 'upload' || activeTab === 'sources',
          'hidden lg:flex': activeTab === 'chat',
        }"
      >
        <!-- Upload Section -->
        <div
          class="border border-primary/15 rounded-xl shadow-none overflow-hidden bg-white/95 backdrop-blur-md text-primary font-sans"
          :class="{
            'flex flex-col flex-1 lg:h-2/5 lg:flex-none':
              activeTab === 'upload',
            'hidden lg:flex lg:flex-col': activeTab !== 'upload',
          }"
        >
          <div
            class="px-4 py-3 border-b border-primary/15 flex items-center justify-between bg-primary/5"
          >
            <h3
              class="text-[10px] font-black uppercase tracking-[0.2em] text-primary flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-primary/80"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" x2="12" y1="3" y2="15" />
              </svg>
              Ingest Data
            </h3>
            <div v-if="uploading" class="flex items-center gap-2">
              <div
                class="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin"
              ></div>
              <span
                class="text-[9px] font-bold text-primary animate-pulse uppercase tracking-widest"
                >Processing</span
              >
            </div>
          </div>

          <div class="flex-1 p-4 flex flex-col">
            <!-- Progress loader area shown when uploading is in progress -->
            <div
              v-if="uploading"
              class="flex-1 border-2 border-primary/20 rounded-lg flex flex-col items-center justify-center p-8 border-double transition-all duration-500 animate-in fade-in zoom-in-95 bg-primary/[0.02]"
            >
              <div class="flex flex-col items-center text-center gap-4 w-full">
                <!-- Premium pulsing and spinning loader -->
                <div
                  class="relative w-16 h-16 flex items-center justify-center"
                >
                  <div
                    class="absolute inset-0 rounded-full border-4 border-primary/10 border-t-primary animate-spin"
                  ></div>
                  <div
                    class="w-10 h-10 bg-primary/10 rounded-full animate-pulse flex items-center justify-center"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      class="text-primary animate-bounce"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" x2="12" y1="3" y2="15" />
                    </svg>
                  </div>
                </div>

                <div class="space-y-2.5 w-full">
                  <p
                    class="text-[11px] font-black uppercase tracking-[0.2em] text-primary animate-pulse"
                  >
                    Ingesting data
                  </p>
                  <!-- Current active step returned from server -->
                  <div
                    class="inline-flex items-center gap-2 px-3 py-1 bg-primary/5 rounded border border-primary/10 shadow-sm"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full bg-primary animate-ping"
                    ></span>
                    <p
                      class="text-[10px] font-bold text-primary uppercase tracking-widest font-mono"
                    >
                      {{ processingStep }}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Standard file dropzone shown when not uploading -->
            <div
              v-else
              class="flex-1 relative border-2 border-dashed border-primary/15 rounded-lg flex flex-col items-center justify-center py-8 px-4 cursor-pointer hover:border-primary/45 hover:bg-primary/[0.02] transition-all duration-500 group/drop"
              :class="{ 'border-primary bg-primary/[0.04]': isDragging }"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleDrop"
              @click="$refs.fileInput.click()"
            >
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                multiple
                @change="handleFileSelect"
              />

              <div class="flex flex-col items-center text-center gap-3">
                <div
                  class="w-12 h-12 bg-primary/5 rounded-lg flex items-center justify-center border border-primary/10 group-hover/drop:border-primary/30 group-hover/drop:scale-110 transition-all duration-500 shadow-sm"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="text-primary/40 group-hover/drop:text-primary transition-colors"
                  >
                    <path
                      d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"
                    />
                    <path d="M12 12v9" />
                    <path d="m16 16-4-4-4 4" />
                  </svg>
                </div>
                <div>
                  <p
                    class="text-[11px] font-bold uppercase tracking-widest text-primary/80 group-hover/drop:text-primary transition-colors font-sans"
                  >
                    {{ isDragging ? "Drop to upload" : "Click or drag files" }}
                  </p>
                  <p
                    class="text-[9px] text-primary/50 font-medium mt-1 uppercase tracking-tighter"
                  >
                    PDF, TXT, MD, DOCX (Max 10MB)
                  </p>
                </div>
              </div>
            </div>

            <div
              v-if="uploadStatus"
              class="mt-3 p-3 rounded-lg text-[10px] font-bold uppercase tracking-tight flex items-center justify-between gap-3 border animate-in slide-in-from-bottom-2 duration-500 shadow-sm backdrop-blur-md relative overflow-hidden group/status"
              :class="
                uploadStatus.error
                  ? 'bg-red-500/10 border-red-500/20 text-red-800'
                  : 'bg-primary/5 border-primary/10 text-primary'
              "
            >
              <div
                class="absolute bottom-0 left-0 h-[2px] bg-current opacity-20 animate-[status-progress_5s_linear_forwards]"
                v-if="!uploadStatus.error"
              ></div>
              <div class="flex items-start gap-2.5">
                <svg
                  v-if="!uploadStatus.error"
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="mt-0.5 shrink-0"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <svg
                  v-else
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="mt-0.5 shrink-0"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" x2="12" y1="8" y2="12" />
                  <line x1="12" x2="12.01" y1="16" y2="16" />
                </svg>
                <span class="leading-tight">{{ uploadStatus.message }}</span>
              </div>
              <button
                @click="uploadStatus = null"
                class="p-1 hover:bg-current/10 rounded transition-colors opacity-40 hover:opacity-100"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Documents List Section -->
        <div
          class="border border-primary/15 rounded-xl shadow-none overflow-hidden bg-white/95 backdrop-blur-md text-primary font-sans"
          :class="{
            'flex flex-col flex-1 lg:h-1/4 lg:flex-none':
              activeTab === 'upload',
            'hidden lg:flex lg:flex-col': activeTab !== 'upload',
          }"
        >
          <div
            class="px-4 py-3 border-b border-primary/15 flex items-center justify-between bg-primary/5"
          >
            <h3
              class="text-[10px] font-black uppercase tracking-[0.2em] text-primary flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-primary/80"
              >
                <path
                  d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"
                />
                <polyline points="14.5 2 14.5 7.5 20 7.5" />
              </svg>
              Active Documents
            </h3>
            <button
              @click="fetchDocuments"
              class="group/btn text-[9px] font-black text-primary/80 hover:text-primary hover:bg-primary/5 bg-white/40 px-2.5 py-1 rounded transition-all flex items-center gap-1.5 uppercase tracking-widest border border-primary/10 shadow-sm"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
                :class="{ 'animate-spin': loadingDocs }"
              >
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                <polyline points="21 3 21 9 15 9" />
              </svg>
              Refresh
            </button>
          </div>

          <div class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
            <div
              v-if="uploadedDocuments.length === 0"
              class="h-full flex flex-col items-center justify-center text-primary/30 italic py-10"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="mb-2 text-primary/20"
              >
                <path
                  d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"
                />
                <polyline points="14.5 2 14.5 7.5 20 7.5" />
                <line x1="8" y1="13" x2="16" y2="13" />
                <line x1="8" y1="17" x2="16" y2="17" />
                <line x1="10" y1="9" x2="8" y2="9" />
              </svg>
              <p
                class="text-[10px] font-bold uppercase tracking-widest text-primary/40"
              >
                Library Empty
              </p>
            </div>

            <div
              v-for="doc in uploadedDocuments"
              :key="doc.doc_id"
              class="group bg-white/40 border border-primary/5 rounded-lg p-2.5 flex items-center justify-between hover:bg-primary/5 hover:border-primary/20 transition-all duration-300 shadow-sm"
            >
              <div class="flex items-center gap-3 min-w-0 pr-2">
                <div
                  class="w-8 h-8 border border-primary/10 rounded flex items-center justify-center shrink-0 group-hover:bg-primary/5 group-hover:border-primary/20 transition-colors shadow-sm"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="text-primary/60 group-hover:text-primary transition-colors"
                  >
                    <path
                      d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"
                    />
                    <polyline points="14.5 2 14.5 7.5 20 7.5" />
                  </svg>
                </div>
                <div class="min-w-0">
                  <div
                    class="text-[11px] font-bold truncate text-primary group-hover:text-primary transition-colors font-sans"
                  >
                    {{ doc.title || doc.source }}
                  </div>
                  <div
                    class="text-[9px] text-primary/50 mt-1 flex items-center gap-3 font-medium uppercase tracking-wider"
                  >
                    <span class="flex items-center gap-1">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="8"
                        height="8"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z" />
                      </svg>
                      {{ doc.chunk_count }} chunks
                    </span>
                    <span class="flex items-center gap-1">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="8"
                        height="8"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      >
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      {{ new Date(doc.ingested_at).toLocaleDateString() }}
                    </span>
                  </div>
                </div>
              </div>
              <button
                @click="deleteDocument(doc.doc_id)"
                class="opacity-0 group-hover:opacity-100 text-red-600/40 hover:text-red-600 transition-all p-2 hover:bg-red-500/10 rounded"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M3 6h18" />
                  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                  <line x1="10" x2="10" y1="11" y2="17" />
                  <line x1="14" x2="14" y1="11" y2="17" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        <!-- Reference Sources Section -->
        <div
          class="border border-primary/15 rounded-xl shadow-none overflow-hidden bg-white/95 backdrop-blur-md text-primary font-sans"
          :class="{
            'flex flex-col flex-1': activeTab === 'sources',
            'hidden lg:flex lg:flex-col lg:flex-1': activeTab !== 'sources',
          }"
        >
          <div
            class="px-4 py-3 border-b border-primary/15 flex items-center justify-between bg-primary/5"
          >
            <h3
              class="text-[10px] font-black uppercase tracking-[0.2em] text-primary flex items-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="text-primary/80"
              >
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path
                  d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"
                />
              </svg>
              Reference Sources
            </h3>
          </div>

          <div
            class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-3"
            ref="sourcesContainer"
          >
            <div
              v-if="!allCitations.length"
              class="h-full flex flex-col items-center justify-center text-primary/30 italic py-10 text-center"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="mb-2 text-primary/20"
              >
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
              <p
                class="text-[10px] font-bold uppercase tracking-widest max-w-[150px] text-primary/40 animate-pulse"
              >
                Contextual sources will appear here
              </p>
            </div>

            <div
              v-for="(cit, idx) in allCitations"
              :key="cit.id"
              :id="'cite-' + idx"
              class="bg-white/40 border border-primary/5 rounded-lg p-3 hover:border-primary/20 hover:bg-primary/5 transition-all duration-300 group cursor-default shadow-sm"
            >
              <div class="flex items-start justify-between gap-2 mb-2">
                <div
                  class="text-[9px] font-black text-primary uppercase tracking-widest flex items-center gap-2"
                >
                  <span
                    class="w-4 h-4 bg-primary text-surface flex items-center justify-center rounded-[2px] text-[8px] font-black"
                  >
                    {{ idx + 1 }}
                  </span>
                  <span
                    class="truncate max-w-[200px] group-hover:text-primary transition-colors font-sans"
                    >{{ cit.source }}</span
                  >
                </div>
                <div
                  v-if="scoreMap[cit.id]"
                  class="text-[8px] text-primary/70 font-mono opacity-0 group-hover:opacity-100 transition-opacity bg-primary/5 px-1 rounded border border-primary/10"
                >
                  {{ scoreMap[cit.id].score_rerank.toFixed(3) }}
                </div>
              </div>
              <div
                v-html="renderMarkdown(cit.text_snippet)"
                class="markdown-content text-[11px] text-primary/80 leading-relaxed line-clamp-3 group-hover:line-clamp-none transition-all duration-500 font-medium"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <main
        class="flex-1 gap-4 overflow-hidden h-full font-sans animate-in fade-in duration-300"
        :class="{
          'flex flex-col': activeTab === 'chat',
          'hidden lg:flex lg:flex-row': activeTab !== 'chat',
        }"
      >
        <!-- Right Area: Chat History -->
        <section
          class="flex-1 border border-primary/15 rounded-xl p-6 shadow-none flex flex-col overflow-hidden relative bg-white/95 backdrop-blur-md"
        >
          <div
            class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent opacity-50 pointer-events-none"
          ></div>

          <!-- Header & Subtitle -->

          <div
            class="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-10 scroll-smooth"
            ref="chatContainer"
          >
            <!-- Empty State -->
            <div
              v-if="!chatMessages.length"
              class="h-full flex flex-col items-center justify-center text-center space-y-8 animate-in fade-in duration-1000"
            >
              <div class="space-y-3">
                <!-- Riverborn styled graphic logo box -->
                <div
                  class="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
                >
                  <img
                    src="~/assets/static/logo.png"
                    alt="Riverborn Logo"
                    class="w-16 h-16 object-contain rounded"
                  />
                </div>
                <h2
                  class="text-[28px] font-schibsted font-semibold tracking-tight text-primary"
                >
                  AI Knowledge Assistant
                </h2>
                <p
                  class="text-text-muted text-xs font-bold uppercase tracking-[0.2em] opacity-60"
                >
                  Ready to analyze your documents
                </p>
              </div>
            </div>

            <!-- Messages -->
            <div
              v-for="(msg, i) in chatMessages"
              :key="i"
              class="flex flex-col gap-3 group/msg animate-in fade-in duration-300"
              :class="msg.role === 'user' ? 'items-end' : 'items-start'"
            >
              <div
                class="text-[9px] font-black uppercase tracking-[0.25em] text-text-muted px-4 group-hover/msg:opacity-100 transition-opacity"
              >
                {{
                  msg.role === "user"
                    ? "User Message"
                    : msg.isSystem
                      ? "System Notification"
                      : "AI Response"
                }}
              </div>
              <div
                class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-none relative overflow-hidden pr-8"
                :class="
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-tr-none border border-primary/5 shadow-none pr-4 font-sans font-medium'
                    : 'bg-white/85 border border-primary/15 backdrop-blur-md rounded-tl-none text-text font-sans'
                "
              >
                <!-- System Notification Close Button -->
                <button
                  v-if="msg.isSystem"
                  @click="chatMessages.splice(i, 1)"
                  class="absolute right-2 top-2 text-primary/40 hover:text-red-500 hover:bg-red-500/10 p-1 rounded-lg transition-all duration-200 z-20"
                  title="Remove Notification"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>

                <!-- System Steps (Collapsible) -->
                <div
                  v-if="
                    msg.role === 'assistant' && msg.steps && msg.steps.length
                  "
                  class="mb-3 rounded-lg border border-border/40 bg-bg/50 p-2.5 max-w-md overflow-hidden transition-all duration-300 shadow-inner"
                >
                  <button
                    @click="msg.showSteps = !msg.showSteps"
                    class="flex items-center justify-between w-full text-[9px] font-black uppercase tracking-wider text-primary hover:opacity-80 transition-opacity"
                  >
                    <span class="flex items-center gap-1.5">
                      <!-- Spinning loader if loading and this is the latest message -->
                      <svg
                        class="animate-spin h-2.5 w-2.5 text-primary"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        v-if="
                          loading &&
                          chatMessages[chatMessages.length - 1] === msg
                        "
                      >
                        <circle
                          class="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          stroke-width="4"
                        ></circle>
                        <path
                          class="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      <!-- Checkmark otherwise -->
                      <svg
                        class="h-2.5 w-2.5 text-primary"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                        v-else
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      System Steps
                    </span>
                    <span
                      class="flex items-center gap-1 font-mono text-[8px] text-text-muted"
                    >
                      {{ msg.steps.length }} step{{
                        msg.steps.length > 1 ? "s" : ""
                      }}
                      <span
                        class="text-[7px] transform transition-transform duration-200"
                        :class="{ 'rotate-180': msg.showSteps }"
                        >▼</span
                      >
                    </span>
                  </button>

                  <div
                    v-if="msg.showSteps !== false"
                    class="mt-2.5 space-y-1.5 border-t border-border/30 pt-2.5 font-mono text-[10px] leading-relaxed text-text/80 animate-in fade-in slide-in-from-top-2 duration-300"
                  >
                    <div
                      v-for="(step, idx) in msg.steps"
                      :key="idx"
                      class="flex items-start gap-2"
                    >
                      <span class="text-primary font-bold">›</span>
                      <span>{{ step }}</span>
                    </div>
                  </div>
                </div>

                <div v-if="msg.role === 'user'" class="font-bold">
                  {{ msg.content }}
                </div>
                <div
                  v-else
                  v-html="msg.content"
                  class="markdown-content prose prose-invert prose-sm max-w-none font-medium text-text"
                ></div>
              </div>
            </div>

            <!-- Loading state bubble -->
            <div
              v-if="
                loading &&
                (!chatMessages.length ||
                  chatMessages[chatMessages.length - 1].role !== 'assistant')
              "
              class="flex flex-col items-start gap-3 animate-in fade-in slide-in-from-bottom-4 duration-500"
            >
              <div
                class="text-[9px] font-black uppercase tracking-[0.25em] text-text-muted px-4"
              >
                Assistant
              </div>
              <div
                class="bg-white/80 border border-border rounded-2xl rounded-tl-none px-6 py-4 flex gap-1.5 items-center backdrop-blur-md shadow-sm"
              >
                <div
                  class="w-2 h-2 bg-primary rounded-full animate-bounce [animation-duration:0.8s]"
                ></div>
                <div
                  class="w-2 h-2 bg-primary rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.2s]"
                ></div>
                <div
                  class="w-2 h-2 bg-primary rounded-full animate-bounce [animation-duration:0.8s] [animation-delay:0.4s]"
                ></div>
              </div>
            </div>
          </div>

          <!-- Chat Input Footer Area -->
          <div
            class="mt-4 pt-4 border-t border-border/30 relative z-10 font-sans"
          >
            <form @submit.prevent="submitQuery" class="relative">
              <textarea
                v-model="query"
                placeholder="Ask me anything about your documents..."
                rows="3"
                class="w-full bg-white/60 border border-primary/15 rounded-xl px-5 py-4 pr-16 text-sm text-text focus:outline-none focus:border-primary/30 focus:bg-white transition-all resize-none custom-scrollbar shadow-inner"
                @keydown.enter.prevent="submitQuery"
              ></textarea>
              <button
                type="submit"
                :disabled="loading || !query.trim()"
                class="absolute right-3 bottom-4 w-10 h-10 bg-primary text-surface rounded-lg flex items-center justify-center hover:bg-primary/90 disabled:bg-primary/5 disabled:text-primary/20 transition-all active:scale-95 border border-primary/5 shadow-none"
              >
                <svg
                  v-if="!loading"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  class="w-4 h-4"
                >
                  <line x1="7" y1="17" x2="17" y2="7"></line>
                  <polyline points="7 7 17 7 17 17"></polyline>
                </svg>
                <div
                  v-else
                  class="w-4 h-4 border-2 border-surface border-t-transparent rounded-full animate-spin"
                ></div>
              </button>
            </form>

            <div
              class="mt-4 flex items-center justify-between text-[9px] font-bold text-text-muted uppercase tracking-[0.15em] px-1"
            >
              <label
                class="flex items-center gap-2.5 cursor-pointer hover:text-text transition-colors group"
              >
                <div class="relative flex items-center">
                  <input
                    type="checkbox"
                    v-model="useStream"
                    class="peer hidden"
                  />
                  <div
                    class="w-9 h-5 bg-primary/10 rounded-full peer-checked:bg-primary transition-all duration-300 border border-primary/5"
                  ></div>
                  <div
                    class="absolute left-0.5 top-0.5 w-4 h-4 bg-white border border-primary/10 rounded-full peer-checked:translate-x-4 peer-checked:bg-surface peer-checked:border-transparent transition-all duration-300 shadow-sm"
                  ></div>
                </div>
                Streaming
              </label>
              <div
                v-if="results?.timings_ms?.total"
                class="flex gap-4 opacity-60 text-[9px]"
              >
                <span>{{ results.timings_ms.total }}ms</span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
const {
  public: { apiUrl },
} = useRuntimeConfig();

const API = apiUrl;

const query = ref("");
const loading = ref(false);
const loadingDocs = ref(false);
const results = ref({
  timings_ms: {},
  citations: [],
  retrieved: [],
  answer: "",
});
const allCitations = ref([]);
const allRetrieved = ref([]);
const chatMessages = ref([]);
const embeddingService = ref("local");
const rerankerService = ref("bge");
const chatContainer = ref(null);
const sourcesContainer = ref(null);
const isDragging = ref(false);
const uploading = ref(false);
const processingStep = ref("");
const uploadStatus = ref(null);
const uploadedDocuments = ref([]);
const useStream = ref(true);
const activeTab = ref("chat");
const showSettings = ref(false);

onMounted(() => {
  fetchDocuments();
  fetchSettings();
  if (chatContainer.value) {
    chatContainer.value.addEventListener("click", handleCitationClick);
  }
});

function handleCitationClick(e) {
  const target = e.target.closest("a");
  if (target && target.hash && target.hash.startsWith("#cite-")) {
    e.preventDefault();
    const index = parseInt(target.hash.split("-")[1]);
    activeTab.value = "sources";
    nextTick(() => {
      scrollToSource(index);
    });
  }
}

function scrollToSource(index) {
  const el = document.getElementById(`cite-${index}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("ring-2", "ring-primary", "bg-primary/10");
    setTimeout(() => {
      el.classList.remove("ring-2", "ring-primary", "bg-primary/10");
    }, 2000);
  }
}

async function fetchDocuments() {
  loadingDocs.value = true;
  try {
    const res = await $fetch(`${API}/documents`);
    uploadedDocuments.value = res;
    console.log(uploadedDocuments.value);
  } catch (err) {
    console.error("Failed to fetch documents", err);
  } finally {
    loadingDocs.value = false;
  }
}

async function deleteDocument(docId) {
  try {
    await $fetch(`${API}/documents/${docId}`, { method: "DELETE" });
    fetchDocuments();
  } catch (err) {
    console.error("Failed to delete document", err);
  }
}

async function uploadFile(file) {
  uploading.value = true;
  uploadStatus.value = null;
  processingStep.value = "File upload done";
  try {
    const formData = new FormData();
    formData.append("file", file);

    // Call the async upload route which starts the process in background
    const initRes = await $fetch(`${API}/ingest/upload`, {
      method: "POST",
      body: formData,
    });

    const taskId = initRes.task_id;
    processingStep.value = initRes.step || "File upload done";

    // Start polling the status endpoint until completed or failed
    let completed = false;
    while (!completed) {
      // Wait for 500ms before polling next
      await new Promise((resolve) => setTimeout(resolve, 500));

      const statusRes = await $fetch(`${API}/ingest/status/${taskId}`);

      if (statusRes.status === "completed") {
        completed = true;
        uploadStatus.value = {
          message: `Uploaded "${file.name}" — ${statusRes.chunk_count} chunks indexed`,
          error: false,
        };
        fetchDocuments();
      } else if (statusRes.status === "failed") {
        completed = true;
        throw new Error(statusRes.error || "Ingestion pipeline failed.");
      } else {
        // Update the current step in the Vue UI!
        processingStep.value = statusRes.step || "Processing...";
      }
    }

    // Auto-hide status after 5 seconds
    setTimeout(() => {
      if (uploadStatus.value && !uploadStatus.value.error) {
        uploadStatus.value = null;
      }
    }, 5000);
  } catch (err) {
    uploadStatus.value = {
      message: `Failed: ${err.message || err}`,
      error: true,
    };
  } finally {
    uploading.value = false;
    processingStep.value = "";
  }
}

function handleDrop(e) {
  isDragging.value = false;
  for (const file of e.dataTransfer.files) {
    uploadFile(file);
  }
}

function handleFileSelect(e) {
  for (const file of e.target.files) {
    uploadFile(file);
  }
  e.target.value = "";
}

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTo({
      top: chatContainer.value.scrollHeight,
      behavior: "smooth",
    });
  }
};

const submitQuery = async () => {
  if (!query.value.trim() || loading.value) return;

  const userPrompt = query.value.trim();
  chatMessages.value.push({ role: "user", content: userPrompt });
  query.value = "";
  scrollToBottom();

  loading.value = true;
  results.value = { timings_ms: {}, citations: [], retrieved: [], answer: "" };

  if (useStream.value) {
    chatMessages.value.push({
      role: "assistant",
      content: "",
      steps: [],
      showSteps: true,
    });
    await submitQueryStream(userPrompt);
  } else {
    try {
      const res = await $fetch(`${API}/query`, {
        method: "POST",
        body: { query: userPrompt, top_k: 8 },
      });
      results.value = res;

      // Append new citations to allCitations
      const newCitations = res.citations || [];
      newCitations.forEach((cit) => {
        const exists = allCitations.value.some((c) => c.id === cit.id);
        if (!exists) {
          allCitations.value.push(cit);
        }
      });

      // Append new retrieved chunks to allRetrieved
      const newRetrieved = res.retrieved || [];
      newRetrieved.forEach((chunk) => {
        const exists = allRetrieved.value.some((r) => r.id === chunk.id);
        if (!exists) {
          allRetrieved.value.push(chunk);
        }
      });

      console.log("Results:", results.value);
      chatMessages.value.push({
        role: "assistant",
        content: processedAnswer.value,
        steps: res.steps || [],
        showSteps: true,
      });
      scrollToBottom();
    } catch (err) {
      chatMessages.value.push({
        role: "assistant",
        content: "Error: " + err.message,
      });
    } finally {
      loading.value = false;
    }
  }
};

const submitQueryStream = async (userPrompt) => {
  try {
    const response = await fetch(`${API}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: userPrompt, top_k: 8 }),
    });
    console.log("Response submit query stream:", response);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = null;
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ") && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            handleSSEEvent(currentEvent, data);
          } catch {}
          currentEvent = null;
        }
      }
    }
  } catch (err) {
    const lastMsg = chatMessages.value[chatMessages.value.length - 1];
    if (lastMsg)
      lastMsg.content += " <span class='text-red-400'>[Stream Error]</span>";
  } finally {
    loading.value = false;
    scrollToBottom();
  }
};

const handleSSEEvent = (event, data) => {
  const assistantMsg = chatMessages.value[chatMessages.value.length - 1];

  if (event === "delta") {
    results.value.answer += data.content;
    assistantMsg.content = processedAnswer.value;
  } else if (event === "status") {
    if (assistantMsg) {
      if (!assistantMsg.steps) {
        assistantMsg.steps = [];
        assistantMsg.showSteps = true;
      }
      if (data.message && !assistantMsg.steps.includes(data.message)) {
        assistantMsg.steps.push(data.message);
      }
    }
  } else if (event === "timings") {
    results.value.timings_ms = data;
  } else if (event === "citations") {
    results.value.citations = data.citations || [];

    // Append new citations to allCitations
    const currentCitations = data.citations || [];
    currentCitations.forEach((cit) => {
      const exists = allCitations.value.some((c) => c.id === cit.id);
      if (!exists) {
        allCitations.value.push(cit);
      }
    });

    assistantMsg.content = processedAnswer.value;
  } else if (event === "retrieved") {
    results.value.retrieved = data.chunks || [];

    // Append new retrieved chunks to allRetrieved
    const currentRetrieved = data.chunks || [];
    currentRetrieved.forEach((chunk) => {
      const exists = allRetrieved.value.some((r) => r.id === chunk.id);
      if (!exists) {
        allRetrieved.value.push(chunk);
      }
    });
  } else if (event === "error") {
    assistantMsg.content = "Error: " + (data.error || "Unknown error");
  }

  scrollToBottom();
};

const scoreMap = computed(() => {
  if (!allRetrieved.value.length) return {};
  return Object.fromEntries(
    allRetrieved.value.map((r) => [
      r.id,
      { score_rerank: r.score_rerank ?? 0, score_rrf: r.score_rrf ?? 0 },
    ]),
  );
});

const escapeHtml = (unsafe) => {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
};

const renderMarkdown = (text) => {
  if (!text) return "";
  let html = text;

  // 1. Code blocks (extract to prevent parsing inside code)
  const codeBlocks = [];
  html = html.replace(/```([\s\S]*?)```/g, (match, p1) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(`<pre><code>${escapeHtml(p1.trim())}</code></pre>`);
    return placeholder;
  });

  // 2. Inline code (extract to prevent parsing inside inline code)
  const inlineCodes = [];
  html = html.replace(/`([^`\n]+)`/g, (match, p1) => {
    const placeholder = `__INLINE_CODE_${inlineCodes.length}__`;
    inlineCodes.push(`<code>${escapeHtml(p1)}</code>`);
    return placeholder;
  });

  // 3. Headers
  html = html.replace(/^### (.*$)/gim, "<h4>$1</h4>");
  html = html.replace(/^## (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^# (.*$)/gim, "<h2>$1</h2>");

  // 4. Blockquotes
  html = html.replace(/^>\s+(.+)$/gm, "<blockquote>$1</blockquote>");

  // 5. Bold & Italics
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // 6. Bullet Lists
  html = html.replace(
    /^\s*[\-\*\+]\s+(.+)$/gm,
    '<li class="list-disc">$1</li>',
  );
  html = html.replace(/(<li class="list-disc">.*<\/li>\s*)+/g, "<ul>$&</ul>");

  // 7. Numbered Lists
  html = html.replace(
    /^\s*\d+\.\s+(.+)$/gm,
    '<li class="list-decimal">$1</li>',
  );
  html = html.replace(
    /(<li class="list-decimal">.*<\/li>\s*)+/g,
    "<ol>$&</ol>",
  );

  // 8. Convert newlines to br tags for normal lines
  html = html.replace(/\n/g, "<br>");

  // 9. Restore inline code and code blocks (replaces placeholders)
  inlineCodes.forEach((val, idx) => {
    html = html.replace(new RegExp(`__INLINE_CODE_${idx}__`, "g"), val);
  });
  codeBlocks.forEach((val, idx) => {
    html = html.replace(new RegExp(`__CODE_BLOCK_${idx}__`, "g"), val);
  });

  return html;
};

const processedAnswer = computed(() => {
  if (!results.value || !results.value.answer) return "";
  let text = results.value.answer;

  if (results.value.citations) {
    results.value.citations.forEach((cit, index) => {
      const globalIndex = allCitations.value.findIndex((c) => c.id === cit.id);
      const displayIndex = globalIndex !== -1 ? globalIndex : index;

      const regex = new RegExp(`\\[${cit.id}\\]`, "g");
      text = text.replace(
        regex,
        `<a href="#cite-${displayIndex}" title="${cit.source}">[${displayIndex + 1}]</a>`,
      );
    });
  }

  text = text.replace(
    /\[[0-9a-f-]{36}\]/g,
    '<span class="inline-block px-1 mx-1 bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 rounded text-[10px] font-bold" title="Invalid Citation">[?]</span>',
  );

  return renderMarkdown(text);
});

const fetchSettings = async () => {
  try {
    const res = await $fetch(`${API}/settings`);
    if (res) {
      if (res.embedding_service) embeddingService.value = res.embedding_service;
      if (res.reranker_service) rerankerService.value = res.reranker_service;
    }
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
};

const setEmbeddingService = async (service) => {
  if (loading.value || uploading.value) return;
  const previousEmbedding = embeddingService.value;
  const previousReranker = rerankerService.value;

  const targetReranker = service === "openai" ? "openai" : "bge";

  embeddingService.value = service;
  rerankerService.value = targetReranker;

  try {
    await $fetch(`${API}/settings`, {
      method: "POST",
      body: {
        embedding_service: service,
        reranker_service: targetReranker,
      },
    });
    allCitations.value = [];
    allRetrieved.value = [];

    const embedName = service === "openai" ? "OpenAI Cloud" : "Local BGE-M3";
    const rerankName =
      targetReranker === "openai"
        ? "OpenAI Cloud (GPT-4o-mini)"
        : "Local BGE Reranker";

    chatMessages.value.push({
      role: "assistant",
      isSystem: true,
      content: `<span class="text-primary font-bold">System Notification:</span> Switched embedding service to <strong>${embedName}</strong> and reranker service to <strong>${rerankName}</strong> (automatically synchronized). Ready for search/ingest under the new semantic vector space!`,
      steps: [],
      showSteps: false,
    });
  } catch (err) {
    console.error("Failed to update settings:", err);
    embeddingService.value = previousEmbedding;
    rerankerService.value = previousReranker;
  }
};
</script>

<style>
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.4);
}
.markdown-content a {
  @apply inline-block px-1.5 mx-0.5 bg-primary/20 text-primary border border-primary/30 rounded text-[10px] font-bold no-underline transition-all hover:bg-primary hover:text-surface hover:-translate-y-0.5 shadow-sm;
}
.markdown-content br {
  @apply mb-2 block content-[''];
}
.markdown-content h2 {
  font-family: "Besley", serif;
  @apply text-base font-extrabold tracking-tight text-primary mt-6 mb-3 border-b border-border/30 pb-1 block;
}
.markdown-content h3 {
  font-family: "Besley", serif;
  @apply text-sm font-extrabold uppercase tracking-wide text-primary mt-5 mb-2.5 border-b border-border/30 pb-1 block;
}
.markdown-content h4 {
  font-family: "Besley", serif;
  @apply text-xs font-extrabold uppercase tracking-wide text-primary mt-4 mb-2 block;
}
.markdown-content code {
  @apply bg-primary/10 border border-primary/20 rounded px-1.5 py-0.5 font-mono text-[11px] text-primary font-bold shadow-sm;
}
.markdown-content pre {
  @apply bg-bg border border-border/50 rounded-lg p-4 my-4 overflow-x-auto font-mono text-[11px] text-text-muted shadow-inner select-all leading-normal custom-scrollbar block;
}
.markdown-content pre code {
  @apply bg-transparent border-0 p-0 font-normal text-text-muted shadow-none font-mono block whitespace-pre;
}
.markdown-content ul {
  @apply my-3 pl-4 space-y-1 block;
}
.markdown-content ol {
  @apply my-3 pl-4 space-y-1 block;
}
.markdown-content li {
  @apply py-0.5 text-text/90 leading-relaxed block;
}
.markdown-content blockquote {
  @apply border-l-4 border-primary/50 pl-3 py-1 my-3 bg-primary/5 rounded-r text-text-muted italic block;
}
.markdown-content strong {
  @apply font-black text-text;
}
.markdown-content em {
  @apply italic opacity-85;
}
@keyframes status-progress {
  from {
    width: 0%;
  }
  to {
    width: 100%;
  }
}
</style>
