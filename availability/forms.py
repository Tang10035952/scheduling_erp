from django import forms
from .models import WorkAvailability
from datetime import date

class WorkAvailabilityForm(forms.ModelForm):
    """
    用於員工填寫可上班意願的表單
    """
    
    # 重新定義 date 欄位，增加日期選擇器提示
    date = forms.DateField(
        label='可上班日期',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': date.today().isoformat() # 限制日期必須大於等於今天
        }),
        initial=date.today()
    )

    # 重新定義時間欄位，增加時間選擇器
    start_time = forms.TimeField(
        label='開始時間',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )

    end_time = forms.TimeField(
        label='結束時間',
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control'
        })
    )

    class Meta:
        model = WorkAvailability
        # 員工只需要填寫這三個欄位
        fields = ['date', 'start_time', 'end_time']
        
    def clean(self):
        """
        自定義表單驗證：確保結束時間晚於開始時間
        """
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            # 檢查結束時間是否晚於開始時間
            if start_time >= end_time:
                msg = "結束時間必須晚於開始時間。"
                # 抛出錯誤到 end_time 欄位
                self.add_error('end_time', msg)
                
            # 檢查意願時長是否合理 (例如：最長不能超過 12 小時)
            # 由於這是 time 欄位，直接比較 datetime 比較複雜，這裡暫時簡化。
            # 如果需要嚴格的時長驗證，需要將日期和時間合併為 datetime 物件來比較。
            
        return cleaned_data