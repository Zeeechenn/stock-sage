// 历史兼容：原型代码曾以 window.React / window.ReactDOM 全局风格编写。
// TS 迁移后所有模块已直接 import react,这里的 window 挂载仅为
// 外部脚本/控制台调试兼容保留,源码内不要再读这两个全局。
import React from 'react'
import * as ReactDOMNS from 'react-dom'
import { createRoot } from 'react-dom/client'

window.React = React
window.ReactDOM = { ...ReactDOMNS, createRoot }
