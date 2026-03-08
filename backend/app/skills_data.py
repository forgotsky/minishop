from typing import List, Dict, Any


SKILLS_DATA: List[Dict[str, Any]] = [
    {
        "categoryId": "primary",
        "categoryName": "小学英语",
        "stage": "3-6年级",
        "topSkills": [
            {
                "skillId": "word-foundation",
                "skillName": "词汇与拼读基础",
                "summary": "高频词识别、发音规则、基础表达",
                "levels": [
                    {
                        "level": "L1",
                        "title": "入门识词与发音",
                        "objective": "认识最常用的课堂与生活词，能读能用。",
                        "points": [
                            "26个字母与基础音素感知",
                            "100个高频词（颜色、数字、家庭、学校）",
                            "简单指令句：Stand up / Open your book",
                            "be动词肯定句：I am..., This is...",
                        ],
                        "microSplit": {
                            "dailyLoad": "30-45分钟/天",
                            "hourlyLoad": "每小时2个词组+2句例句+1个应用任务",
                            "hourTasks": [
                                {
                                    "slot": "第1小时",
                                    "words": ["book", "pen", "desk", "chair", "bag", "ruler"],
                                    "wordsText": "book / pen / desk / chair / bag / ruler",
                                    "sentence": "This is my book.",
                                    "usage": "用3个教室物品做指认介绍。",
                                },
                                {
                                    "slot": "第2小时",
                                    "words": ["red", "blue", "yellow", "green", "black", "white"],
                                    "wordsText": "red / blue / yellow / green / black / white",
                                    "sentence": "My bag is blue.",
                                    "usage": "描述你身边2个物品的颜色。",
                                },
                                {
                                    "slot": "第3小时",
                                    "words": ["one", "two", "three", "four", "five", "ten"],
                                    "wordsText": "one / two / three / four / five / ten",
                                    "sentence": "I have three pens.",
                                    "usage": "数文具并说完整句。",
                                },
                                {
                                    "slot": "第4小时",
                                    "words": ["father", "mother", "brother", "sister", "grandma", "grandpa"],
                                    "wordsText": "father / mother / brother / sister / grandma / grandpa",
                                    "sentence": "She is my mother.",
                                    "usage": "用家庭照片做6句介绍。",
                                },
                            ],
                            "dayTasks": [
                                {
                                    "day": "Day 1",
                                    "target": "课堂物品词汇 + This is句型",
                                    "deliverable": "掌握6词，完成3句口头介绍。",
                                },
                                {
                                    "day": "Day 2",
                                    "target": "颜色词汇 + is描述",
                                    "deliverable": "掌握6词，完成2句颜色描述。",
                                },
                                {
                                    "day": "Day 3",
                                    "target": "数字词汇 + I have句型",
                                    "deliverable": "掌握6词，完成3句数量表达。",
                                },
                                {
                                    "day": "Day 4",
                                    "target": "家庭词汇 + She/He is句型",
                                    "deliverable": "掌握6词，完成家庭成员介绍。",
                                },
                            ],
                        },
                    },
                    {
                        "level": "L2",
                        "title": "词块积累",
                        "objective": "能把词汇组合成固定表达。",
                        "points": ["200-300词汇量", "时间/天气/爱好主题词块", "一般现在时基础问答"],
                    },
                    {
                        "level": "L3",
                        "title": "句型扩展",
                        "objective": "能描述日常活动和简单计划。",
                        "points": ["频率副词", "there be结构", "情态动词can"],
                    },
                    {
                        "level": "L4",
                        "title": "段落表达",
                        "objective": "围绕一个主题写4-6句。",
                        "points": ["连接词and/but/because", "时态一致性", "自我检查拼写"],
                    },
                    {
                        "level": "L5",
                        "title": "阅读迁移",
                        "objective": "能从短文提取关键信息并复述。",
                        "points": ["略读找主题", "细节定位", "关键词复述"],
                    },
                    {
                        "level": "L6",
                        "title": "任务化输出",
                        "objective": "完成简单项目式任务。",
                        "points": ["海报说明", "情景对话", "口头展示"],
                    },
                ],
            },
            {
                "skillId": "listening-speaking",
                "skillName": "听说互动",
                "summary": "课堂对话、问答反应、情景表达",
                "levels": [
                    {
                        "level": "L1",
                        "title": "跟读与问候",
                        "objective": "完成基础问候对话",
                        "points": ["Hello/How are you", "跟读模仿", "课堂问答反应"],
                    },
                    {
                        "level": "L2",
                        "title": "替换表达",
                        "objective": "替换关键词完成对话",
                        "points": ["人称替换", "地点替换", "时间替换"],
                    },
                    {
                        "level": "L3",
                        "title": "半开放表达",
                        "objective": "按主题回答2-3句",
                        "points": ["兴趣", "家庭", "校园活动"],
                    },
                    {
                        "level": "L4",
                        "title": "情景对话",
                        "objective": "完成校园和生活场景沟通",
                        "points": ["购物", "问路", "邀请"],
                    },
                    {
                        "level": "L5",
                        "title": "听后复述",
                        "objective": "听短文后复述要点",
                        "points": ["抓关键词", "逻辑顺序", "口头总结"],
                    },
                    {
                        "level": "L6",
                        "title": "小组展示",
                        "objective": "完成1-2分钟主题展示",
                        "points": ["分工表达", "过渡句", "提问回应"],
                    },
                ],
            },
            {
                "skillId": "reading-writing",
                "skillName": "读写启蒙",
                "summary": "短文理解与句子写作",
                "levels": [
                    {
                        "level": "L1",
                        "title": "看图写句",
                        "objective": "围绕图片写1-2句",
                        "points": ["主谓宾基础", "名词单复数", "句末标点"],
                    },
                    {
                        "level": "L2",
                        "title": "句子拼接",
                        "objective": "把词组拼成完整句",
                        "points": ["词序", "be动词", "冠词a/an"],
                    },
                    {
                        "level": "L3",
                        "title": "短文理解",
                        "objective": "读50-80词短文并答题",
                        "points": ["事实题", "词义猜测", "时间地点定位"],
                    },
                    {
                        "level": "L4",
                        "title": "段落写作",
                        "objective": "写4-5句主题段落",
                        "points": ["主题句", "支持句", "结尾句"],
                    },
                    {
                        "level": "L5",
                        "title": "读写结合",
                        "objective": "根据阅读完成仿写",
                        "points": ["句型借鉴", "词汇迁移", "结构模仿"],
                    },
                    {
                        "level": "L6",
                        "title": "任务写作",
                        "objective": "完成通知/贺卡/日记",
                        "points": ["格式", "对象意识", "信息完整"],
                    },
                ],
            },
        ],
    },
    {
        "categoryId": "junior",
        "categoryName": "初中英语",
        "stage": "7-9年级",
        "topSkills": [
            {
                "skillId": "grammar-sentence",
                "skillName": "语法与句型应用",
                "summary": "核心语法 + 中考常见句型",
                "levels": [
                    {
                        "level": "L1",
                        "title": "核心时态入门",
                        "objective": "现在时/过去时正确成句",
                        "points": ["一般现在时", "一般过去时", "第三人称单数"],
                    },
                    {
                        "level": "L2",
                        "title": "进行时与将来时",
                        "objective": "表达正在发生与计划",
                        "points": ["现在进行时", "be going to", "will"],
                    },
                    {
                        "level": "L3",
                        "title": "复合句起步",
                        "objective": "能使用宾语从句和状语从句",
                        "points": ["that/if引导宾语从句", "when/because从句"],
                    },
                    {
                        "level": "L4",
                        "title": "语法整合",
                        "objective": "在短文中保持时态一致",
                        "points": ["被动语态基础", "非谓语入门", "一致性检查"],
                    },
                    {
                        "level": "L5",
                        "title": "中考句型迁移",
                        "objective": "把语法用于阅读与写作",
                        "points": ["同义改写", "句型转换", "语篇衔接"],
                    },
                    {
                        "level": "L6",
                        "title": "复杂表达",
                        "objective": "完成逻辑清晰的短文表达",
                        "points": ["并列与从属结合", "逻辑连词", "语言准确性"],
                    },
                ],
            },
            {
                "skillId": "reading-strategy",
                "skillName": "阅读策略",
                "summary": "完形/阅读理解策略化训练",
                "levels": [
                    {
                        "level": "L1",
                        "title": "信息定位",
                        "objective": "快速定位题干信息",
                        "points": ["关键词匹配", "段落首句", "题干回文"],
                    },
                    {
                        "level": "L2",
                        "title": "上下文猜词",
                        "objective": "依据语境判断词义",
                        "points": ["同义线索", "反义线索", "定义线索"],
                    },
                    {
                        "level": "L3",
                        "title": "逻辑关系识别",
                        "objective": "识别转折/因果/递进",
                        "points": ["however", "therefore", "in addition"],
                    },
                    {
                        "level": "L4",
                        "title": "主旨与态度",
                        "objective": "判断主旨和作者态度",
                        "points": ["主题句", "语气词", "情感色彩"],
                    },
                    {
                        "level": "L5",
                        "title": "题型协同",
                        "objective": "同篇文章多题型联动",
                        "points": ["细节题", "推理题", "主旨题"],
                    },
                    {
                        "level": "L6",
                        "title": "限时实战",
                        "objective": "在限时内稳定高正确率",
                        "points": ["时间分配", "错题复盘", "策略固化"],
                    },
                ],
            },
            {
                "skillId": "writing-expression",
                "skillName": "写作表达",
                "summary": "中考写作框架与语言升级",
                "levels": [
                    {
                        "level": "L1",
                        "title": "句子正确",
                        "objective": "保证句法和拼写正确",
                        "points": ["主谓一致", "时态正确", "常错词修正"],
                    },
                    {
                        "level": "L2",
                        "title": "段落完整",
                        "objective": "写出有开头主体结尾的段落",
                        "points": ["主题句", "细节句", "收束句"],
                    },
                    {
                        "level": "L3",
                        "title": "连接与逻辑",
                        "objective": "增强段间衔接",
                        "points": ["first/next/finally", "because/so", "although"],
                    },
                    {
                        "level": "L4",
                        "title": "语言升级",
                        "objective": "使用多样句式",
                        "points": ["定语从句入门", "非谓语短语", "同义替换"],
                    },
                    {
                        "level": "L5",
                        "title": "应用文模板",
                        "objective": "掌握通知/建议信/日记",
                        "points": ["格式", "语域", "信息覆盖"],
                    },
                    {
                        "level": "L6",
                        "title": "个性化表达",
                        "objective": "在规范内体现观点深度",
                        "points": ["观点-论据-例子", "反思句", "结尾升华"],
                    },
                ],
            },
        ],
    },
    {
        "categoryId": "senior",
        "categoryName": "高中英语",
        "stage": "10-12年级",
        "topSkills": [
            {
                "skillId": "advanced-reading",
                "skillName": "深度阅读与信息处理",
                "summary": "高考阅读、七选五、语篇分析",
                "levels": [
                    {
                        "level": "L1",
                        "title": "基础抓取",
                        "objective": "准确获取事实信息",
                        "points": ["细节定位", "代词指代", "主题识别"],
                    },
                    {
                        "level": "L2",
                        "title": "逻辑推断",
                        "objective": "完成隐含信息判断",
                        "points": ["因果推断", "态度推断", "目的推断"],
                    },
                    {
                        "level": "L3",
                        "title": "结构分析",
                        "objective": "分析段落结构与功能",
                        "points": ["总分总", "并列递进", "问题-解决"],
                    },
                    {
                        "level": "L4",
                        "title": "跨段整合",
                        "objective": "整合多段信息回答综合题",
                        "points": ["信息归并", "证据链", "选项排除"],
                    },
                    {
                        "level": "L5",
                        "title": "限时策略",
                        "objective": "按题型优化时间",
                        "points": ["先易后难", "关键句优先", "卡点跳过"],
                    },
                    {
                        "level": "L6",
                        "title": "高分稳态",
                        "objective": "保持稳定高正确率与速度",
                        "points": ["错因模型", "复盘模板", "专项回炉"],
                    },
                ],
            },
            {
                "skillId": "grammar-fill",
                "skillName": "语法填空与语言知识",
                "summary": "词法句法综合应用",
                "levels": [
                    {
                        "level": "L1",
                        "title": "词性判断",
                        "objective": "根据空格判断词性",
                        "points": ["名词/动词/形容词", "副词位置", "冠词判断"],
                    },
                    {
                        "level": "L2",
                        "title": "时态语态",
                        "objective": "准确变形",
                        "points": ["时态一致", "被动语态", "主谓一致"],
                    },
                    {
                        "level": "L3",
                        "title": "非谓语",
                        "objective": "区分to do/doing/done",
                        "points": ["作主语", "作定语", "作状语"],
                    },
                    {
                        "level": "L4",
                        "title": "从句",
                        "objective": "掌握三大从句",
                        "points": ["定语从句", "名词性从句", "状语从句"],
                    },
                    {
                        "level": "L5",
                        "title": "语篇层面",
                        "objective": "结合上下文完成填空",
                        "points": ["照应关系", "逻辑连词", "语义一致"],
                    },
                    {
                        "level": "L6",
                        "title": "综合提速",
                        "objective": "提升准确率和速度",
                        "points": ["步骤化解题", "易错点清单", "限时练"],
                    },
                ],
            },
            {
                "skillId": "writing-upgrade",
                "skillName": "高阶写作表达",
                "summary": "应用文 + 读后续写/概要写作",
                "levels": [
                    {
                        "level": "L1",
                        "title": "信息完整",
                        "objective": "确保题目要求全覆盖",
                        "points": ["审题清单", "要点映射", "字数控制"],
                    },
                    {
                        "level": "L2",
                        "title": "结构稳定",
                        "objective": "形成固定写作骨架",
                        "points": ["开头-主体-结尾", "段落主题句", "逻辑连接"],
                    },
                    {
                        "level": "L3",
                        "title": "语言多样",
                        "objective": "用多样句式表达同一意思",
                        "points": ["倒装/强调", "从句扩展", "短语替换"],
                    },
                    {
                        "level": "L4",
                        "title": "内容深化",
                        "objective": "增加细节与理由",
                        "points": ["例证", "比较", "因果链"],
                    },
                    {
                        "level": "L5",
                        "title": "任务专项",
                        "objective": "针对题型高频训练",
                        "points": ["建议信", "活动报道", "续写"],
                    },
                    {
                        "level": "L6",
                        "title": "评分对齐",
                        "objective": "按评分标准优化",
                        "points": ["语言准确", "内容质量", "篇章连贯"],
                    },
                ],
            },
        ],
    },
]


def get_skills() -> List[Dict[str, Any]]:
    return SKILLS_DATA
