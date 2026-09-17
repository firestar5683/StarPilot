#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_4115870174312830998) {
   out_4115870174312830998[0] = delta_x[0] + nom_x[0];
   out_4115870174312830998[1] = delta_x[1] + nom_x[1];
   out_4115870174312830998[2] = delta_x[2] + nom_x[2];
   out_4115870174312830998[3] = delta_x[3] + nom_x[3];
   out_4115870174312830998[4] = delta_x[4] + nom_x[4];
   out_4115870174312830998[5] = delta_x[5] + nom_x[5];
   out_4115870174312830998[6] = delta_x[6] + nom_x[6];
   out_4115870174312830998[7] = delta_x[7] + nom_x[7];
   out_4115870174312830998[8] = delta_x[8] + nom_x[8];
   out_4115870174312830998[9] = delta_x[9] + nom_x[9];
   out_4115870174312830998[10] = delta_x[10] + nom_x[10];
   out_4115870174312830998[11] = delta_x[11] + nom_x[11];
   out_4115870174312830998[12] = delta_x[12] + nom_x[12];
   out_4115870174312830998[13] = delta_x[13] + nom_x[13];
   out_4115870174312830998[14] = delta_x[14] + nom_x[14];
   out_4115870174312830998[15] = delta_x[15] + nom_x[15];
   out_4115870174312830998[16] = delta_x[16] + nom_x[16];
   out_4115870174312830998[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_2299838754417090386) {
   out_2299838754417090386[0] = -nom_x[0] + true_x[0];
   out_2299838754417090386[1] = -nom_x[1] + true_x[1];
   out_2299838754417090386[2] = -nom_x[2] + true_x[2];
   out_2299838754417090386[3] = -nom_x[3] + true_x[3];
   out_2299838754417090386[4] = -nom_x[4] + true_x[4];
   out_2299838754417090386[5] = -nom_x[5] + true_x[5];
   out_2299838754417090386[6] = -nom_x[6] + true_x[6];
   out_2299838754417090386[7] = -nom_x[7] + true_x[7];
   out_2299838754417090386[8] = -nom_x[8] + true_x[8];
   out_2299838754417090386[9] = -nom_x[9] + true_x[9];
   out_2299838754417090386[10] = -nom_x[10] + true_x[10];
   out_2299838754417090386[11] = -nom_x[11] + true_x[11];
   out_2299838754417090386[12] = -nom_x[12] + true_x[12];
   out_2299838754417090386[13] = -nom_x[13] + true_x[13];
   out_2299838754417090386[14] = -nom_x[14] + true_x[14];
   out_2299838754417090386[15] = -nom_x[15] + true_x[15];
   out_2299838754417090386[16] = -nom_x[16] + true_x[16];
   out_2299838754417090386[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_652375008318869169) {
   out_652375008318869169[0] = 1.0;
   out_652375008318869169[1] = 0.0;
   out_652375008318869169[2] = 0.0;
   out_652375008318869169[3] = 0.0;
   out_652375008318869169[4] = 0.0;
   out_652375008318869169[5] = 0.0;
   out_652375008318869169[6] = 0.0;
   out_652375008318869169[7] = 0.0;
   out_652375008318869169[8] = 0.0;
   out_652375008318869169[9] = 0.0;
   out_652375008318869169[10] = 0.0;
   out_652375008318869169[11] = 0.0;
   out_652375008318869169[12] = 0.0;
   out_652375008318869169[13] = 0.0;
   out_652375008318869169[14] = 0.0;
   out_652375008318869169[15] = 0.0;
   out_652375008318869169[16] = 0.0;
   out_652375008318869169[17] = 0.0;
   out_652375008318869169[18] = 0.0;
   out_652375008318869169[19] = 1.0;
   out_652375008318869169[20] = 0.0;
   out_652375008318869169[21] = 0.0;
   out_652375008318869169[22] = 0.0;
   out_652375008318869169[23] = 0.0;
   out_652375008318869169[24] = 0.0;
   out_652375008318869169[25] = 0.0;
   out_652375008318869169[26] = 0.0;
   out_652375008318869169[27] = 0.0;
   out_652375008318869169[28] = 0.0;
   out_652375008318869169[29] = 0.0;
   out_652375008318869169[30] = 0.0;
   out_652375008318869169[31] = 0.0;
   out_652375008318869169[32] = 0.0;
   out_652375008318869169[33] = 0.0;
   out_652375008318869169[34] = 0.0;
   out_652375008318869169[35] = 0.0;
   out_652375008318869169[36] = 0.0;
   out_652375008318869169[37] = 0.0;
   out_652375008318869169[38] = 1.0;
   out_652375008318869169[39] = 0.0;
   out_652375008318869169[40] = 0.0;
   out_652375008318869169[41] = 0.0;
   out_652375008318869169[42] = 0.0;
   out_652375008318869169[43] = 0.0;
   out_652375008318869169[44] = 0.0;
   out_652375008318869169[45] = 0.0;
   out_652375008318869169[46] = 0.0;
   out_652375008318869169[47] = 0.0;
   out_652375008318869169[48] = 0.0;
   out_652375008318869169[49] = 0.0;
   out_652375008318869169[50] = 0.0;
   out_652375008318869169[51] = 0.0;
   out_652375008318869169[52] = 0.0;
   out_652375008318869169[53] = 0.0;
   out_652375008318869169[54] = 0.0;
   out_652375008318869169[55] = 0.0;
   out_652375008318869169[56] = 0.0;
   out_652375008318869169[57] = 1.0;
   out_652375008318869169[58] = 0.0;
   out_652375008318869169[59] = 0.0;
   out_652375008318869169[60] = 0.0;
   out_652375008318869169[61] = 0.0;
   out_652375008318869169[62] = 0.0;
   out_652375008318869169[63] = 0.0;
   out_652375008318869169[64] = 0.0;
   out_652375008318869169[65] = 0.0;
   out_652375008318869169[66] = 0.0;
   out_652375008318869169[67] = 0.0;
   out_652375008318869169[68] = 0.0;
   out_652375008318869169[69] = 0.0;
   out_652375008318869169[70] = 0.0;
   out_652375008318869169[71] = 0.0;
   out_652375008318869169[72] = 0.0;
   out_652375008318869169[73] = 0.0;
   out_652375008318869169[74] = 0.0;
   out_652375008318869169[75] = 0.0;
   out_652375008318869169[76] = 1.0;
   out_652375008318869169[77] = 0.0;
   out_652375008318869169[78] = 0.0;
   out_652375008318869169[79] = 0.0;
   out_652375008318869169[80] = 0.0;
   out_652375008318869169[81] = 0.0;
   out_652375008318869169[82] = 0.0;
   out_652375008318869169[83] = 0.0;
   out_652375008318869169[84] = 0.0;
   out_652375008318869169[85] = 0.0;
   out_652375008318869169[86] = 0.0;
   out_652375008318869169[87] = 0.0;
   out_652375008318869169[88] = 0.0;
   out_652375008318869169[89] = 0.0;
   out_652375008318869169[90] = 0.0;
   out_652375008318869169[91] = 0.0;
   out_652375008318869169[92] = 0.0;
   out_652375008318869169[93] = 0.0;
   out_652375008318869169[94] = 0.0;
   out_652375008318869169[95] = 1.0;
   out_652375008318869169[96] = 0.0;
   out_652375008318869169[97] = 0.0;
   out_652375008318869169[98] = 0.0;
   out_652375008318869169[99] = 0.0;
   out_652375008318869169[100] = 0.0;
   out_652375008318869169[101] = 0.0;
   out_652375008318869169[102] = 0.0;
   out_652375008318869169[103] = 0.0;
   out_652375008318869169[104] = 0.0;
   out_652375008318869169[105] = 0.0;
   out_652375008318869169[106] = 0.0;
   out_652375008318869169[107] = 0.0;
   out_652375008318869169[108] = 0.0;
   out_652375008318869169[109] = 0.0;
   out_652375008318869169[110] = 0.0;
   out_652375008318869169[111] = 0.0;
   out_652375008318869169[112] = 0.0;
   out_652375008318869169[113] = 0.0;
   out_652375008318869169[114] = 1.0;
   out_652375008318869169[115] = 0.0;
   out_652375008318869169[116] = 0.0;
   out_652375008318869169[117] = 0.0;
   out_652375008318869169[118] = 0.0;
   out_652375008318869169[119] = 0.0;
   out_652375008318869169[120] = 0.0;
   out_652375008318869169[121] = 0.0;
   out_652375008318869169[122] = 0.0;
   out_652375008318869169[123] = 0.0;
   out_652375008318869169[124] = 0.0;
   out_652375008318869169[125] = 0.0;
   out_652375008318869169[126] = 0.0;
   out_652375008318869169[127] = 0.0;
   out_652375008318869169[128] = 0.0;
   out_652375008318869169[129] = 0.0;
   out_652375008318869169[130] = 0.0;
   out_652375008318869169[131] = 0.0;
   out_652375008318869169[132] = 0.0;
   out_652375008318869169[133] = 1.0;
   out_652375008318869169[134] = 0.0;
   out_652375008318869169[135] = 0.0;
   out_652375008318869169[136] = 0.0;
   out_652375008318869169[137] = 0.0;
   out_652375008318869169[138] = 0.0;
   out_652375008318869169[139] = 0.0;
   out_652375008318869169[140] = 0.0;
   out_652375008318869169[141] = 0.0;
   out_652375008318869169[142] = 0.0;
   out_652375008318869169[143] = 0.0;
   out_652375008318869169[144] = 0.0;
   out_652375008318869169[145] = 0.0;
   out_652375008318869169[146] = 0.0;
   out_652375008318869169[147] = 0.0;
   out_652375008318869169[148] = 0.0;
   out_652375008318869169[149] = 0.0;
   out_652375008318869169[150] = 0.0;
   out_652375008318869169[151] = 0.0;
   out_652375008318869169[152] = 1.0;
   out_652375008318869169[153] = 0.0;
   out_652375008318869169[154] = 0.0;
   out_652375008318869169[155] = 0.0;
   out_652375008318869169[156] = 0.0;
   out_652375008318869169[157] = 0.0;
   out_652375008318869169[158] = 0.0;
   out_652375008318869169[159] = 0.0;
   out_652375008318869169[160] = 0.0;
   out_652375008318869169[161] = 0.0;
   out_652375008318869169[162] = 0.0;
   out_652375008318869169[163] = 0.0;
   out_652375008318869169[164] = 0.0;
   out_652375008318869169[165] = 0.0;
   out_652375008318869169[166] = 0.0;
   out_652375008318869169[167] = 0.0;
   out_652375008318869169[168] = 0.0;
   out_652375008318869169[169] = 0.0;
   out_652375008318869169[170] = 0.0;
   out_652375008318869169[171] = 1.0;
   out_652375008318869169[172] = 0.0;
   out_652375008318869169[173] = 0.0;
   out_652375008318869169[174] = 0.0;
   out_652375008318869169[175] = 0.0;
   out_652375008318869169[176] = 0.0;
   out_652375008318869169[177] = 0.0;
   out_652375008318869169[178] = 0.0;
   out_652375008318869169[179] = 0.0;
   out_652375008318869169[180] = 0.0;
   out_652375008318869169[181] = 0.0;
   out_652375008318869169[182] = 0.0;
   out_652375008318869169[183] = 0.0;
   out_652375008318869169[184] = 0.0;
   out_652375008318869169[185] = 0.0;
   out_652375008318869169[186] = 0.0;
   out_652375008318869169[187] = 0.0;
   out_652375008318869169[188] = 0.0;
   out_652375008318869169[189] = 0.0;
   out_652375008318869169[190] = 1.0;
   out_652375008318869169[191] = 0.0;
   out_652375008318869169[192] = 0.0;
   out_652375008318869169[193] = 0.0;
   out_652375008318869169[194] = 0.0;
   out_652375008318869169[195] = 0.0;
   out_652375008318869169[196] = 0.0;
   out_652375008318869169[197] = 0.0;
   out_652375008318869169[198] = 0.0;
   out_652375008318869169[199] = 0.0;
   out_652375008318869169[200] = 0.0;
   out_652375008318869169[201] = 0.0;
   out_652375008318869169[202] = 0.0;
   out_652375008318869169[203] = 0.0;
   out_652375008318869169[204] = 0.0;
   out_652375008318869169[205] = 0.0;
   out_652375008318869169[206] = 0.0;
   out_652375008318869169[207] = 0.0;
   out_652375008318869169[208] = 0.0;
   out_652375008318869169[209] = 1.0;
   out_652375008318869169[210] = 0.0;
   out_652375008318869169[211] = 0.0;
   out_652375008318869169[212] = 0.0;
   out_652375008318869169[213] = 0.0;
   out_652375008318869169[214] = 0.0;
   out_652375008318869169[215] = 0.0;
   out_652375008318869169[216] = 0.0;
   out_652375008318869169[217] = 0.0;
   out_652375008318869169[218] = 0.0;
   out_652375008318869169[219] = 0.0;
   out_652375008318869169[220] = 0.0;
   out_652375008318869169[221] = 0.0;
   out_652375008318869169[222] = 0.0;
   out_652375008318869169[223] = 0.0;
   out_652375008318869169[224] = 0.0;
   out_652375008318869169[225] = 0.0;
   out_652375008318869169[226] = 0.0;
   out_652375008318869169[227] = 0.0;
   out_652375008318869169[228] = 1.0;
   out_652375008318869169[229] = 0.0;
   out_652375008318869169[230] = 0.0;
   out_652375008318869169[231] = 0.0;
   out_652375008318869169[232] = 0.0;
   out_652375008318869169[233] = 0.0;
   out_652375008318869169[234] = 0.0;
   out_652375008318869169[235] = 0.0;
   out_652375008318869169[236] = 0.0;
   out_652375008318869169[237] = 0.0;
   out_652375008318869169[238] = 0.0;
   out_652375008318869169[239] = 0.0;
   out_652375008318869169[240] = 0.0;
   out_652375008318869169[241] = 0.0;
   out_652375008318869169[242] = 0.0;
   out_652375008318869169[243] = 0.0;
   out_652375008318869169[244] = 0.0;
   out_652375008318869169[245] = 0.0;
   out_652375008318869169[246] = 0.0;
   out_652375008318869169[247] = 1.0;
   out_652375008318869169[248] = 0.0;
   out_652375008318869169[249] = 0.0;
   out_652375008318869169[250] = 0.0;
   out_652375008318869169[251] = 0.0;
   out_652375008318869169[252] = 0.0;
   out_652375008318869169[253] = 0.0;
   out_652375008318869169[254] = 0.0;
   out_652375008318869169[255] = 0.0;
   out_652375008318869169[256] = 0.0;
   out_652375008318869169[257] = 0.0;
   out_652375008318869169[258] = 0.0;
   out_652375008318869169[259] = 0.0;
   out_652375008318869169[260] = 0.0;
   out_652375008318869169[261] = 0.0;
   out_652375008318869169[262] = 0.0;
   out_652375008318869169[263] = 0.0;
   out_652375008318869169[264] = 0.0;
   out_652375008318869169[265] = 0.0;
   out_652375008318869169[266] = 1.0;
   out_652375008318869169[267] = 0.0;
   out_652375008318869169[268] = 0.0;
   out_652375008318869169[269] = 0.0;
   out_652375008318869169[270] = 0.0;
   out_652375008318869169[271] = 0.0;
   out_652375008318869169[272] = 0.0;
   out_652375008318869169[273] = 0.0;
   out_652375008318869169[274] = 0.0;
   out_652375008318869169[275] = 0.0;
   out_652375008318869169[276] = 0.0;
   out_652375008318869169[277] = 0.0;
   out_652375008318869169[278] = 0.0;
   out_652375008318869169[279] = 0.0;
   out_652375008318869169[280] = 0.0;
   out_652375008318869169[281] = 0.0;
   out_652375008318869169[282] = 0.0;
   out_652375008318869169[283] = 0.0;
   out_652375008318869169[284] = 0.0;
   out_652375008318869169[285] = 1.0;
   out_652375008318869169[286] = 0.0;
   out_652375008318869169[287] = 0.0;
   out_652375008318869169[288] = 0.0;
   out_652375008318869169[289] = 0.0;
   out_652375008318869169[290] = 0.0;
   out_652375008318869169[291] = 0.0;
   out_652375008318869169[292] = 0.0;
   out_652375008318869169[293] = 0.0;
   out_652375008318869169[294] = 0.0;
   out_652375008318869169[295] = 0.0;
   out_652375008318869169[296] = 0.0;
   out_652375008318869169[297] = 0.0;
   out_652375008318869169[298] = 0.0;
   out_652375008318869169[299] = 0.0;
   out_652375008318869169[300] = 0.0;
   out_652375008318869169[301] = 0.0;
   out_652375008318869169[302] = 0.0;
   out_652375008318869169[303] = 0.0;
   out_652375008318869169[304] = 1.0;
   out_652375008318869169[305] = 0.0;
   out_652375008318869169[306] = 0.0;
   out_652375008318869169[307] = 0.0;
   out_652375008318869169[308] = 0.0;
   out_652375008318869169[309] = 0.0;
   out_652375008318869169[310] = 0.0;
   out_652375008318869169[311] = 0.0;
   out_652375008318869169[312] = 0.0;
   out_652375008318869169[313] = 0.0;
   out_652375008318869169[314] = 0.0;
   out_652375008318869169[315] = 0.0;
   out_652375008318869169[316] = 0.0;
   out_652375008318869169[317] = 0.0;
   out_652375008318869169[318] = 0.0;
   out_652375008318869169[319] = 0.0;
   out_652375008318869169[320] = 0.0;
   out_652375008318869169[321] = 0.0;
   out_652375008318869169[322] = 0.0;
   out_652375008318869169[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1837308153381576760) {
   out_1837308153381576760[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1837308153381576760[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1837308153381576760[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1837308153381576760[3] = dt*state[12] + state[3];
   out_1837308153381576760[4] = dt*state[13] + state[4];
   out_1837308153381576760[5] = dt*state[14] + state[5];
   out_1837308153381576760[6] = state[6];
   out_1837308153381576760[7] = state[7];
   out_1837308153381576760[8] = state[8];
   out_1837308153381576760[9] = state[9];
   out_1837308153381576760[10] = state[10];
   out_1837308153381576760[11] = state[11];
   out_1837308153381576760[12] = state[12];
   out_1837308153381576760[13] = state[13];
   out_1837308153381576760[14] = state[14];
   out_1837308153381576760[15] = state[15];
   out_1837308153381576760[16] = state[16];
   out_1837308153381576760[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4411443613772384488) {
   out_4411443613772384488[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4411443613772384488[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4411443613772384488[2] = 0;
   out_4411443613772384488[3] = 0;
   out_4411443613772384488[4] = 0;
   out_4411443613772384488[5] = 0;
   out_4411443613772384488[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4411443613772384488[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4411443613772384488[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4411443613772384488[9] = 0;
   out_4411443613772384488[10] = 0;
   out_4411443613772384488[11] = 0;
   out_4411443613772384488[12] = 0;
   out_4411443613772384488[13] = 0;
   out_4411443613772384488[14] = 0;
   out_4411443613772384488[15] = 0;
   out_4411443613772384488[16] = 0;
   out_4411443613772384488[17] = 0;
   out_4411443613772384488[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4411443613772384488[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4411443613772384488[20] = 0;
   out_4411443613772384488[21] = 0;
   out_4411443613772384488[22] = 0;
   out_4411443613772384488[23] = 0;
   out_4411443613772384488[24] = 0;
   out_4411443613772384488[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4411443613772384488[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4411443613772384488[27] = 0;
   out_4411443613772384488[28] = 0;
   out_4411443613772384488[29] = 0;
   out_4411443613772384488[30] = 0;
   out_4411443613772384488[31] = 0;
   out_4411443613772384488[32] = 0;
   out_4411443613772384488[33] = 0;
   out_4411443613772384488[34] = 0;
   out_4411443613772384488[35] = 0;
   out_4411443613772384488[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4411443613772384488[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4411443613772384488[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4411443613772384488[39] = 0;
   out_4411443613772384488[40] = 0;
   out_4411443613772384488[41] = 0;
   out_4411443613772384488[42] = 0;
   out_4411443613772384488[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4411443613772384488[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4411443613772384488[45] = 0;
   out_4411443613772384488[46] = 0;
   out_4411443613772384488[47] = 0;
   out_4411443613772384488[48] = 0;
   out_4411443613772384488[49] = 0;
   out_4411443613772384488[50] = 0;
   out_4411443613772384488[51] = 0;
   out_4411443613772384488[52] = 0;
   out_4411443613772384488[53] = 0;
   out_4411443613772384488[54] = 0;
   out_4411443613772384488[55] = 0;
   out_4411443613772384488[56] = 0;
   out_4411443613772384488[57] = 1;
   out_4411443613772384488[58] = 0;
   out_4411443613772384488[59] = 0;
   out_4411443613772384488[60] = 0;
   out_4411443613772384488[61] = 0;
   out_4411443613772384488[62] = 0;
   out_4411443613772384488[63] = 0;
   out_4411443613772384488[64] = 0;
   out_4411443613772384488[65] = 0;
   out_4411443613772384488[66] = dt;
   out_4411443613772384488[67] = 0;
   out_4411443613772384488[68] = 0;
   out_4411443613772384488[69] = 0;
   out_4411443613772384488[70] = 0;
   out_4411443613772384488[71] = 0;
   out_4411443613772384488[72] = 0;
   out_4411443613772384488[73] = 0;
   out_4411443613772384488[74] = 0;
   out_4411443613772384488[75] = 0;
   out_4411443613772384488[76] = 1;
   out_4411443613772384488[77] = 0;
   out_4411443613772384488[78] = 0;
   out_4411443613772384488[79] = 0;
   out_4411443613772384488[80] = 0;
   out_4411443613772384488[81] = 0;
   out_4411443613772384488[82] = 0;
   out_4411443613772384488[83] = 0;
   out_4411443613772384488[84] = 0;
   out_4411443613772384488[85] = dt;
   out_4411443613772384488[86] = 0;
   out_4411443613772384488[87] = 0;
   out_4411443613772384488[88] = 0;
   out_4411443613772384488[89] = 0;
   out_4411443613772384488[90] = 0;
   out_4411443613772384488[91] = 0;
   out_4411443613772384488[92] = 0;
   out_4411443613772384488[93] = 0;
   out_4411443613772384488[94] = 0;
   out_4411443613772384488[95] = 1;
   out_4411443613772384488[96] = 0;
   out_4411443613772384488[97] = 0;
   out_4411443613772384488[98] = 0;
   out_4411443613772384488[99] = 0;
   out_4411443613772384488[100] = 0;
   out_4411443613772384488[101] = 0;
   out_4411443613772384488[102] = 0;
   out_4411443613772384488[103] = 0;
   out_4411443613772384488[104] = dt;
   out_4411443613772384488[105] = 0;
   out_4411443613772384488[106] = 0;
   out_4411443613772384488[107] = 0;
   out_4411443613772384488[108] = 0;
   out_4411443613772384488[109] = 0;
   out_4411443613772384488[110] = 0;
   out_4411443613772384488[111] = 0;
   out_4411443613772384488[112] = 0;
   out_4411443613772384488[113] = 0;
   out_4411443613772384488[114] = 1;
   out_4411443613772384488[115] = 0;
   out_4411443613772384488[116] = 0;
   out_4411443613772384488[117] = 0;
   out_4411443613772384488[118] = 0;
   out_4411443613772384488[119] = 0;
   out_4411443613772384488[120] = 0;
   out_4411443613772384488[121] = 0;
   out_4411443613772384488[122] = 0;
   out_4411443613772384488[123] = 0;
   out_4411443613772384488[124] = 0;
   out_4411443613772384488[125] = 0;
   out_4411443613772384488[126] = 0;
   out_4411443613772384488[127] = 0;
   out_4411443613772384488[128] = 0;
   out_4411443613772384488[129] = 0;
   out_4411443613772384488[130] = 0;
   out_4411443613772384488[131] = 0;
   out_4411443613772384488[132] = 0;
   out_4411443613772384488[133] = 1;
   out_4411443613772384488[134] = 0;
   out_4411443613772384488[135] = 0;
   out_4411443613772384488[136] = 0;
   out_4411443613772384488[137] = 0;
   out_4411443613772384488[138] = 0;
   out_4411443613772384488[139] = 0;
   out_4411443613772384488[140] = 0;
   out_4411443613772384488[141] = 0;
   out_4411443613772384488[142] = 0;
   out_4411443613772384488[143] = 0;
   out_4411443613772384488[144] = 0;
   out_4411443613772384488[145] = 0;
   out_4411443613772384488[146] = 0;
   out_4411443613772384488[147] = 0;
   out_4411443613772384488[148] = 0;
   out_4411443613772384488[149] = 0;
   out_4411443613772384488[150] = 0;
   out_4411443613772384488[151] = 0;
   out_4411443613772384488[152] = 1;
   out_4411443613772384488[153] = 0;
   out_4411443613772384488[154] = 0;
   out_4411443613772384488[155] = 0;
   out_4411443613772384488[156] = 0;
   out_4411443613772384488[157] = 0;
   out_4411443613772384488[158] = 0;
   out_4411443613772384488[159] = 0;
   out_4411443613772384488[160] = 0;
   out_4411443613772384488[161] = 0;
   out_4411443613772384488[162] = 0;
   out_4411443613772384488[163] = 0;
   out_4411443613772384488[164] = 0;
   out_4411443613772384488[165] = 0;
   out_4411443613772384488[166] = 0;
   out_4411443613772384488[167] = 0;
   out_4411443613772384488[168] = 0;
   out_4411443613772384488[169] = 0;
   out_4411443613772384488[170] = 0;
   out_4411443613772384488[171] = 1;
   out_4411443613772384488[172] = 0;
   out_4411443613772384488[173] = 0;
   out_4411443613772384488[174] = 0;
   out_4411443613772384488[175] = 0;
   out_4411443613772384488[176] = 0;
   out_4411443613772384488[177] = 0;
   out_4411443613772384488[178] = 0;
   out_4411443613772384488[179] = 0;
   out_4411443613772384488[180] = 0;
   out_4411443613772384488[181] = 0;
   out_4411443613772384488[182] = 0;
   out_4411443613772384488[183] = 0;
   out_4411443613772384488[184] = 0;
   out_4411443613772384488[185] = 0;
   out_4411443613772384488[186] = 0;
   out_4411443613772384488[187] = 0;
   out_4411443613772384488[188] = 0;
   out_4411443613772384488[189] = 0;
   out_4411443613772384488[190] = 1;
   out_4411443613772384488[191] = 0;
   out_4411443613772384488[192] = 0;
   out_4411443613772384488[193] = 0;
   out_4411443613772384488[194] = 0;
   out_4411443613772384488[195] = 0;
   out_4411443613772384488[196] = 0;
   out_4411443613772384488[197] = 0;
   out_4411443613772384488[198] = 0;
   out_4411443613772384488[199] = 0;
   out_4411443613772384488[200] = 0;
   out_4411443613772384488[201] = 0;
   out_4411443613772384488[202] = 0;
   out_4411443613772384488[203] = 0;
   out_4411443613772384488[204] = 0;
   out_4411443613772384488[205] = 0;
   out_4411443613772384488[206] = 0;
   out_4411443613772384488[207] = 0;
   out_4411443613772384488[208] = 0;
   out_4411443613772384488[209] = 1;
   out_4411443613772384488[210] = 0;
   out_4411443613772384488[211] = 0;
   out_4411443613772384488[212] = 0;
   out_4411443613772384488[213] = 0;
   out_4411443613772384488[214] = 0;
   out_4411443613772384488[215] = 0;
   out_4411443613772384488[216] = 0;
   out_4411443613772384488[217] = 0;
   out_4411443613772384488[218] = 0;
   out_4411443613772384488[219] = 0;
   out_4411443613772384488[220] = 0;
   out_4411443613772384488[221] = 0;
   out_4411443613772384488[222] = 0;
   out_4411443613772384488[223] = 0;
   out_4411443613772384488[224] = 0;
   out_4411443613772384488[225] = 0;
   out_4411443613772384488[226] = 0;
   out_4411443613772384488[227] = 0;
   out_4411443613772384488[228] = 1;
   out_4411443613772384488[229] = 0;
   out_4411443613772384488[230] = 0;
   out_4411443613772384488[231] = 0;
   out_4411443613772384488[232] = 0;
   out_4411443613772384488[233] = 0;
   out_4411443613772384488[234] = 0;
   out_4411443613772384488[235] = 0;
   out_4411443613772384488[236] = 0;
   out_4411443613772384488[237] = 0;
   out_4411443613772384488[238] = 0;
   out_4411443613772384488[239] = 0;
   out_4411443613772384488[240] = 0;
   out_4411443613772384488[241] = 0;
   out_4411443613772384488[242] = 0;
   out_4411443613772384488[243] = 0;
   out_4411443613772384488[244] = 0;
   out_4411443613772384488[245] = 0;
   out_4411443613772384488[246] = 0;
   out_4411443613772384488[247] = 1;
   out_4411443613772384488[248] = 0;
   out_4411443613772384488[249] = 0;
   out_4411443613772384488[250] = 0;
   out_4411443613772384488[251] = 0;
   out_4411443613772384488[252] = 0;
   out_4411443613772384488[253] = 0;
   out_4411443613772384488[254] = 0;
   out_4411443613772384488[255] = 0;
   out_4411443613772384488[256] = 0;
   out_4411443613772384488[257] = 0;
   out_4411443613772384488[258] = 0;
   out_4411443613772384488[259] = 0;
   out_4411443613772384488[260] = 0;
   out_4411443613772384488[261] = 0;
   out_4411443613772384488[262] = 0;
   out_4411443613772384488[263] = 0;
   out_4411443613772384488[264] = 0;
   out_4411443613772384488[265] = 0;
   out_4411443613772384488[266] = 1;
   out_4411443613772384488[267] = 0;
   out_4411443613772384488[268] = 0;
   out_4411443613772384488[269] = 0;
   out_4411443613772384488[270] = 0;
   out_4411443613772384488[271] = 0;
   out_4411443613772384488[272] = 0;
   out_4411443613772384488[273] = 0;
   out_4411443613772384488[274] = 0;
   out_4411443613772384488[275] = 0;
   out_4411443613772384488[276] = 0;
   out_4411443613772384488[277] = 0;
   out_4411443613772384488[278] = 0;
   out_4411443613772384488[279] = 0;
   out_4411443613772384488[280] = 0;
   out_4411443613772384488[281] = 0;
   out_4411443613772384488[282] = 0;
   out_4411443613772384488[283] = 0;
   out_4411443613772384488[284] = 0;
   out_4411443613772384488[285] = 1;
   out_4411443613772384488[286] = 0;
   out_4411443613772384488[287] = 0;
   out_4411443613772384488[288] = 0;
   out_4411443613772384488[289] = 0;
   out_4411443613772384488[290] = 0;
   out_4411443613772384488[291] = 0;
   out_4411443613772384488[292] = 0;
   out_4411443613772384488[293] = 0;
   out_4411443613772384488[294] = 0;
   out_4411443613772384488[295] = 0;
   out_4411443613772384488[296] = 0;
   out_4411443613772384488[297] = 0;
   out_4411443613772384488[298] = 0;
   out_4411443613772384488[299] = 0;
   out_4411443613772384488[300] = 0;
   out_4411443613772384488[301] = 0;
   out_4411443613772384488[302] = 0;
   out_4411443613772384488[303] = 0;
   out_4411443613772384488[304] = 1;
   out_4411443613772384488[305] = 0;
   out_4411443613772384488[306] = 0;
   out_4411443613772384488[307] = 0;
   out_4411443613772384488[308] = 0;
   out_4411443613772384488[309] = 0;
   out_4411443613772384488[310] = 0;
   out_4411443613772384488[311] = 0;
   out_4411443613772384488[312] = 0;
   out_4411443613772384488[313] = 0;
   out_4411443613772384488[314] = 0;
   out_4411443613772384488[315] = 0;
   out_4411443613772384488[316] = 0;
   out_4411443613772384488[317] = 0;
   out_4411443613772384488[318] = 0;
   out_4411443613772384488[319] = 0;
   out_4411443613772384488[320] = 0;
   out_4411443613772384488[321] = 0;
   out_4411443613772384488[322] = 0;
   out_4411443613772384488[323] = 1;
}
void h_4(double *state, double *unused, double *out_8735933422126784440) {
   out_8735933422126784440[0] = state[6] + state[9];
   out_8735933422126784440[1] = state[7] + state[10];
   out_8735933422126784440[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_2621847070472080084) {
   out_2621847070472080084[0] = 0;
   out_2621847070472080084[1] = 0;
   out_2621847070472080084[2] = 0;
   out_2621847070472080084[3] = 0;
   out_2621847070472080084[4] = 0;
   out_2621847070472080084[5] = 0;
   out_2621847070472080084[6] = 1;
   out_2621847070472080084[7] = 0;
   out_2621847070472080084[8] = 0;
   out_2621847070472080084[9] = 1;
   out_2621847070472080084[10] = 0;
   out_2621847070472080084[11] = 0;
   out_2621847070472080084[12] = 0;
   out_2621847070472080084[13] = 0;
   out_2621847070472080084[14] = 0;
   out_2621847070472080084[15] = 0;
   out_2621847070472080084[16] = 0;
   out_2621847070472080084[17] = 0;
   out_2621847070472080084[18] = 0;
   out_2621847070472080084[19] = 0;
   out_2621847070472080084[20] = 0;
   out_2621847070472080084[21] = 0;
   out_2621847070472080084[22] = 0;
   out_2621847070472080084[23] = 0;
   out_2621847070472080084[24] = 0;
   out_2621847070472080084[25] = 1;
   out_2621847070472080084[26] = 0;
   out_2621847070472080084[27] = 0;
   out_2621847070472080084[28] = 1;
   out_2621847070472080084[29] = 0;
   out_2621847070472080084[30] = 0;
   out_2621847070472080084[31] = 0;
   out_2621847070472080084[32] = 0;
   out_2621847070472080084[33] = 0;
   out_2621847070472080084[34] = 0;
   out_2621847070472080084[35] = 0;
   out_2621847070472080084[36] = 0;
   out_2621847070472080084[37] = 0;
   out_2621847070472080084[38] = 0;
   out_2621847070472080084[39] = 0;
   out_2621847070472080084[40] = 0;
   out_2621847070472080084[41] = 0;
   out_2621847070472080084[42] = 0;
   out_2621847070472080084[43] = 0;
   out_2621847070472080084[44] = 1;
   out_2621847070472080084[45] = 0;
   out_2621847070472080084[46] = 0;
   out_2621847070472080084[47] = 1;
   out_2621847070472080084[48] = 0;
   out_2621847070472080084[49] = 0;
   out_2621847070472080084[50] = 0;
   out_2621847070472080084[51] = 0;
   out_2621847070472080084[52] = 0;
   out_2621847070472080084[53] = 0;
}
void h_10(double *state, double *unused, double *out_6171703416781276782) {
   out_6171703416781276782[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_6171703416781276782[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_6171703416781276782[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8600432860711518676) {
   out_8600432860711518676[0] = 0;
   out_8600432860711518676[1] = 9.8100000000000005*cos(state[1]);
   out_8600432860711518676[2] = 0;
   out_8600432860711518676[3] = 0;
   out_8600432860711518676[4] = -state[8];
   out_8600432860711518676[5] = state[7];
   out_8600432860711518676[6] = 0;
   out_8600432860711518676[7] = state[5];
   out_8600432860711518676[8] = -state[4];
   out_8600432860711518676[9] = 0;
   out_8600432860711518676[10] = 0;
   out_8600432860711518676[11] = 0;
   out_8600432860711518676[12] = 1;
   out_8600432860711518676[13] = 0;
   out_8600432860711518676[14] = 0;
   out_8600432860711518676[15] = 1;
   out_8600432860711518676[16] = 0;
   out_8600432860711518676[17] = 0;
   out_8600432860711518676[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8600432860711518676[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8600432860711518676[20] = 0;
   out_8600432860711518676[21] = state[8];
   out_8600432860711518676[22] = 0;
   out_8600432860711518676[23] = -state[6];
   out_8600432860711518676[24] = -state[5];
   out_8600432860711518676[25] = 0;
   out_8600432860711518676[26] = state[3];
   out_8600432860711518676[27] = 0;
   out_8600432860711518676[28] = 0;
   out_8600432860711518676[29] = 0;
   out_8600432860711518676[30] = 0;
   out_8600432860711518676[31] = 1;
   out_8600432860711518676[32] = 0;
   out_8600432860711518676[33] = 0;
   out_8600432860711518676[34] = 1;
   out_8600432860711518676[35] = 0;
   out_8600432860711518676[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8600432860711518676[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8600432860711518676[38] = 0;
   out_8600432860711518676[39] = -state[7];
   out_8600432860711518676[40] = state[6];
   out_8600432860711518676[41] = 0;
   out_8600432860711518676[42] = state[4];
   out_8600432860711518676[43] = -state[3];
   out_8600432860711518676[44] = 0;
   out_8600432860711518676[45] = 0;
   out_8600432860711518676[46] = 0;
   out_8600432860711518676[47] = 0;
   out_8600432860711518676[48] = 0;
   out_8600432860711518676[49] = 0;
   out_8600432860711518676[50] = 1;
   out_8600432860711518676[51] = 0;
   out_8600432860711518676[52] = 0;
   out_8600432860711518676[53] = 1;
}
void h_13(double *state, double *unused, double *out_7399425647141855355) {
   out_7399425647141855355[0] = state[3];
   out_7399425647141855355[1] = state[4];
   out_7399425647141855355[2] = state[5];
}
void H_13(double *state, double *unused, double *out_590426754860252717) {
   out_590426754860252717[0] = 0;
   out_590426754860252717[1] = 0;
   out_590426754860252717[2] = 0;
   out_590426754860252717[3] = 1;
   out_590426754860252717[4] = 0;
   out_590426754860252717[5] = 0;
   out_590426754860252717[6] = 0;
   out_590426754860252717[7] = 0;
   out_590426754860252717[8] = 0;
   out_590426754860252717[9] = 0;
   out_590426754860252717[10] = 0;
   out_590426754860252717[11] = 0;
   out_590426754860252717[12] = 0;
   out_590426754860252717[13] = 0;
   out_590426754860252717[14] = 0;
   out_590426754860252717[15] = 0;
   out_590426754860252717[16] = 0;
   out_590426754860252717[17] = 0;
   out_590426754860252717[18] = 0;
   out_590426754860252717[19] = 0;
   out_590426754860252717[20] = 0;
   out_590426754860252717[21] = 0;
   out_590426754860252717[22] = 1;
   out_590426754860252717[23] = 0;
   out_590426754860252717[24] = 0;
   out_590426754860252717[25] = 0;
   out_590426754860252717[26] = 0;
   out_590426754860252717[27] = 0;
   out_590426754860252717[28] = 0;
   out_590426754860252717[29] = 0;
   out_590426754860252717[30] = 0;
   out_590426754860252717[31] = 0;
   out_590426754860252717[32] = 0;
   out_590426754860252717[33] = 0;
   out_590426754860252717[34] = 0;
   out_590426754860252717[35] = 0;
   out_590426754860252717[36] = 0;
   out_590426754860252717[37] = 0;
   out_590426754860252717[38] = 0;
   out_590426754860252717[39] = 0;
   out_590426754860252717[40] = 0;
   out_590426754860252717[41] = 1;
   out_590426754860252717[42] = 0;
   out_590426754860252717[43] = 0;
   out_590426754860252717[44] = 0;
   out_590426754860252717[45] = 0;
   out_590426754860252717[46] = 0;
   out_590426754860252717[47] = 0;
   out_590426754860252717[48] = 0;
   out_590426754860252717[49] = 0;
   out_590426754860252717[50] = 0;
   out_590426754860252717[51] = 0;
   out_590426754860252717[52] = 0;
   out_590426754860252717[53] = 0;
}
void h_14(double *state, double *unused, double *out_7752950954395433666) {
   out_7752950954395433666[0] = state[6];
   out_7752950954395433666[1] = state[7];
   out_7752950954395433666[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1341393785867404445) {
   out_1341393785867404445[0] = 0;
   out_1341393785867404445[1] = 0;
   out_1341393785867404445[2] = 0;
   out_1341393785867404445[3] = 0;
   out_1341393785867404445[4] = 0;
   out_1341393785867404445[5] = 0;
   out_1341393785867404445[6] = 1;
   out_1341393785867404445[7] = 0;
   out_1341393785867404445[8] = 0;
   out_1341393785867404445[9] = 0;
   out_1341393785867404445[10] = 0;
   out_1341393785867404445[11] = 0;
   out_1341393785867404445[12] = 0;
   out_1341393785867404445[13] = 0;
   out_1341393785867404445[14] = 0;
   out_1341393785867404445[15] = 0;
   out_1341393785867404445[16] = 0;
   out_1341393785867404445[17] = 0;
   out_1341393785867404445[18] = 0;
   out_1341393785867404445[19] = 0;
   out_1341393785867404445[20] = 0;
   out_1341393785867404445[21] = 0;
   out_1341393785867404445[22] = 0;
   out_1341393785867404445[23] = 0;
   out_1341393785867404445[24] = 0;
   out_1341393785867404445[25] = 1;
   out_1341393785867404445[26] = 0;
   out_1341393785867404445[27] = 0;
   out_1341393785867404445[28] = 0;
   out_1341393785867404445[29] = 0;
   out_1341393785867404445[30] = 0;
   out_1341393785867404445[31] = 0;
   out_1341393785867404445[32] = 0;
   out_1341393785867404445[33] = 0;
   out_1341393785867404445[34] = 0;
   out_1341393785867404445[35] = 0;
   out_1341393785867404445[36] = 0;
   out_1341393785867404445[37] = 0;
   out_1341393785867404445[38] = 0;
   out_1341393785867404445[39] = 0;
   out_1341393785867404445[40] = 0;
   out_1341393785867404445[41] = 0;
   out_1341393785867404445[42] = 0;
   out_1341393785867404445[43] = 0;
   out_1341393785867404445[44] = 1;
   out_1341393785867404445[45] = 0;
   out_1341393785867404445[46] = 0;
   out_1341393785867404445[47] = 0;
   out_1341393785867404445[48] = 0;
   out_1341393785867404445[49] = 0;
   out_1341393785867404445[50] = 0;
   out_1341393785867404445[51] = 0;
   out_1341393785867404445[52] = 0;
   out_1341393785867404445[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_4115870174312830998) {
  err_fun(nom_x, delta_x, out_4115870174312830998);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2299838754417090386) {
  inv_err_fun(nom_x, true_x, out_2299838754417090386);
}
void pose_H_mod_fun(double *state, double *out_652375008318869169) {
  H_mod_fun(state, out_652375008318869169);
}
void pose_f_fun(double *state, double dt, double *out_1837308153381576760) {
  f_fun(state,  dt, out_1837308153381576760);
}
void pose_F_fun(double *state, double dt, double *out_4411443613772384488) {
  F_fun(state,  dt, out_4411443613772384488);
}
void pose_h_4(double *state, double *unused, double *out_8735933422126784440) {
  h_4(state, unused, out_8735933422126784440);
}
void pose_H_4(double *state, double *unused, double *out_2621847070472080084) {
  H_4(state, unused, out_2621847070472080084);
}
void pose_h_10(double *state, double *unused, double *out_6171703416781276782) {
  h_10(state, unused, out_6171703416781276782);
}
void pose_H_10(double *state, double *unused, double *out_8600432860711518676) {
  H_10(state, unused, out_8600432860711518676);
}
void pose_h_13(double *state, double *unused, double *out_7399425647141855355) {
  h_13(state, unused, out_7399425647141855355);
}
void pose_H_13(double *state, double *unused, double *out_590426754860252717) {
  H_13(state, unused, out_590426754860252717);
}
void pose_h_14(double *state, double *unused, double *out_7752950954395433666) {
  h_14(state, unused, out_7752950954395433666);
}
void pose_H_14(double *state, double *unused, double *out_1341393785867404445) {
  H_14(state, unused, out_1341393785867404445);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
