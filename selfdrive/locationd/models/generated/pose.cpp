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
void err_fun(double *nom_x, double *delta_x, double *out_7992688260990922493) {
   out_7992688260990922493[0] = delta_x[0] + nom_x[0];
   out_7992688260990922493[1] = delta_x[1] + nom_x[1];
   out_7992688260990922493[2] = delta_x[2] + nom_x[2];
   out_7992688260990922493[3] = delta_x[3] + nom_x[3];
   out_7992688260990922493[4] = delta_x[4] + nom_x[4];
   out_7992688260990922493[5] = delta_x[5] + nom_x[5];
   out_7992688260990922493[6] = delta_x[6] + nom_x[6];
   out_7992688260990922493[7] = delta_x[7] + nom_x[7];
   out_7992688260990922493[8] = delta_x[8] + nom_x[8];
   out_7992688260990922493[9] = delta_x[9] + nom_x[9];
   out_7992688260990922493[10] = delta_x[10] + nom_x[10];
   out_7992688260990922493[11] = delta_x[11] + nom_x[11];
   out_7992688260990922493[12] = delta_x[12] + nom_x[12];
   out_7992688260990922493[13] = delta_x[13] + nom_x[13];
   out_7992688260990922493[14] = delta_x[14] + nom_x[14];
   out_7992688260990922493[15] = delta_x[15] + nom_x[15];
   out_7992688260990922493[16] = delta_x[16] + nom_x[16];
   out_7992688260990922493[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5809721741941332225) {
   out_5809721741941332225[0] = -nom_x[0] + true_x[0];
   out_5809721741941332225[1] = -nom_x[1] + true_x[1];
   out_5809721741941332225[2] = -nom_x[2] + true_x[2];
   out_5809721741941332225[3] = -nom_x[3] + true_x[3];
   out_5809721741941332225[4] = -nom_x[4] + true_x[4];
   out_5809721741941332225[5] = -nom_x[5] + true_x[5];
   out_5809721741941332225[6] = -nom_x[6] + true_x[6];
   out_5809721741941332225[7] = -nom_x[7] + true_x[7];
   out_5809721741941332225[8] = -nom_x[8] + true_x[8];
   out_5809721741941332225[9] = -nom_x[9] + true_x[9];
   out_5809721741941332225[10] = -nom_x[10] + true_x[10];
   out_5809721741941332225[11] = -nom_x[11] + true_x[11];
   out_5809721741941332225[12] = -nom_x[12] + true_x[12];
   out_5809721741941332225[13] = -nom_x[13] + true_x[13];
   out_5809721741941332225[14] = -nom_x[14] + true_x[14];
   out_5809721741941332225[15] = -nom_x[15] + true_x[15];
   out_5809721741941332225[16] = -nom_x[16] + true_x[16];
   out_5809721741941332225[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_653094641834631323) {
   out_653094641834631323[0] = 1.0;
   out_653094641834631323[1] = 0.0;
   out_653094641834631323[2] = 0.0;
   out_653094641834631323[3] = 0.0;
   out_653094641834631323[4] = 0.0;
   out_653094641834631323[5] = 0.0;
   out_653094641834631323[6] = 0.0;
   out_653094641834631323[7] = 0.0;
   out_653094641834631323[8] = 0.0;
   out_653094641834631323[9] = 0.0;
   out_653094641834631323[10] = 0.0;
   out_653094641834631323[11] = 0.0;
   out_653094641834631323[12] = 0.0;
   out_653094641834631323[13] = 0.0;
   out_653094641834631323[14] = 0.0;
   out_653094641834631323[15] = 0.0;
   out_653094641834631323[16] = 0.0;
   out_653094641834631323[17] = 0.0;
   out_653094641834631323[18] = 0.0;
   out_653094641834631323[19] = 1.0;
   out_653094641834631323[20] = 0.0;
   out_653094641834631323[21] = 0.0;
   out_653094641834631323[22] = 0.0;
   out_653094641834631323[23] = 0.0;
   out_653094641834631323[24] = 0.0;
   out_653094641834631323[25] = 0.0;
   out_653094641834631323[26] = 0.0;
   out_653094641834631323[27] = 0.0;
   out_653094641834631323[28] = 0.0;
   out_653094641834631323[29] = 0.0;
   out_653094641834631323[30] = 0.0;
   out_653094641834631323[31] = 0.0;
   out_653094641834631323[32] = 0.0;
   out_653094641834631323[33] = 0.0;
   out_653094641834631323[34] = 0.0;
   out_653094641834631323[35] = 0.0;
   out_653094641834631323[36] = 0.0;
   out_653094641834631323[37] = 0.0;
   out_653094641834631323[38] = 1.0;
   out_653094641834631323[39] = 0.0;
   out_653094641834631323[40] = 0.0;
   out_653094641834631323[41] = 0.0;
   out_653094641834631323[42] = 0.0;
   out_653094641834631323[43] = 0.0;
   out_653094641834631323[44] = 0.0;
   out_653094641834631323[45] = 0.0;
   out_653094641834631323[46] = 0.0;
   out_653094641834631323[47] = 0.0;
   out_653094641834631323[48] = 0.0;
   out_653094641834631323[49] = 0.0;
   out_653094641834631323[50] = 0.0;
   out_653094641834631323[51] = 0.0;
   out_653094641834631323[52] = 0.0;
   out_653094641834631323[53] = 0.0;
   out_653094641834631323[54] = 0.0;
   out_653094641834631323[55] = 0.0;
   out_653094641834631323[56] = 0.0;
   out_653094641834631323[57] = 1.0;
   out_653094641834631323[58] = 0.0;
   out_653094641834631323[59] = 0.0;
   out_653094641834631323[60] = 0.0;
   out_653094641834631323[61] = 0.0;
   out_653094641834631323[62] = 0.0;
   out_653094641834631323[63] = 0.0;
   out_653094641834631323[64] = 0.0;
   out_653094641834631323[65] = 0.0;
   out_653094641834631323[66] = 0.0;
   out_653094641834631323[67] = 0.0;
   out_653094641834631323[68] = 0.0;
   out_653094641834631323[69] = 0.0;
   out_653094641834631323[70] = 0.0;
   out_653094641834631323[71] = 0.0;
   out_653094641834631323[72] = 0.0;
   out_653094641834631323[73] = 0.0;
   out_653094641834631323[74] = 0.0;
   out_653094641834631323[75] = 0.0;
   out_653094641834631323[76] = 1.0;
   out_653094641834631323[77] = 0.0;
   out_653094641834631323[78] = 0.0;
   out_653094641834631323[79] = 0.0;
   out_653094641834631323[80] = 0.0;
   out_653094641834631323[81] = 0.0;
   out_653094641834631323[82] = 0.0;
   out_653094641834631323[83] = 0.0;
   out_653094641834631323[84] = 0.0;
   out_653094641834631323[85] = 0.0;
   out_653094641834631323[86] = 0.0;
   out_653094641834631323[87] = 0.0;
   out_653094641834631323[88] = 0.0;
   out_653094641834631323[89] = 0.0;
   out_653094641834631323[90] = 0.0;
   out_653094641834631323[91] = 0.0;
   out_653094641834631323[92] = 0.0;
   out_653094641834631323[93] = 0.0;
   out_653094641834631323[94] = 0.0;
   out_653094641834631323[95] = 1.0;
   out_653094641834631323[96] = 0.0;
   out_653094641834631323[97] = 0.0;
   out_653094641834631323[98] = 0.0;
   out_653094641834631323[99] = 0.0;
   out_653094641834631323[100] = 0.0;
   out_653094641834631323[101] = 0.0;
   out_653094641834631323[102] = 0.0;
   out_653094641834631323[103] = 0.0;
   out_653094641834631323[104] = 0.0;
   out_653094641834631323[105] = 0.0;
   out_653094641834631323[106] = 0.0;
   out_653094641834631323[107] = 0.0;
   out_653094641834631323[108] = 0.0;
   out_653094641834631323[109] = 0.0;
   out_653094641834631323[110] = 0.0;
   out_653094641834631323[111] = 0.0;
   out_653094641834631323[112] = 0.0;
   out_653094641834631323[113] = 0.0;
   out_653094641834631323[114] = 1.0;
   out_653094641834631323[115] = 0.0;
   out_653094641834631323[116] = 0.0;
   out_653094641834631323[117] = 0.0;
   out_653094641834631323[118] = 0.0;
   out_653094641834631323[119] = 0.0;
   out_653094641834631323[120] = 0.0;
   out_653094641834631323[121] = 0.0;
   out_653094641834631323[122] = 0.0;
   out_653094641834631323[123] = 0.0;
   out_653094641834631323[124] = 0.0;
   out_653094641834631323[125] = 0.0;
   out_653094641834631323[126] = 0.0;
   out_653094641834631323[127] = 0.0;
   out_653094641834631323[128] = 0.0;
   out_653094641834631323[129] = 0.0;
   out_653094641834631323[130] = 0.0;
   out_653094641834631323[131] = 0.0;
   out_653094641834631323[132] = 0.0;
   out_653094641834631323[133] = 1.0;
   out_653094641834631323[134] = 0.0;
   out_653094641834631323[135] = 0.0;
   out_653094641834631323[136] = 0.0;
   out_653094641834631323[137] = 0.0;
   out_653094641834631323[138] = 0.0;
   out_653094641834631323[139] = 0.0;
   out_653094641834631323[140] = 0.0;
   out_653094641834631323[141] = 0.0;
   out_653094641834631323[142] = 0.0;
   out_653094641834631323[143] = 0.0;
   out_653094641834631323[144] = 0.0;
   out_653094641834631323[145] = 0.0;
   out_653094641834631323[146] = 0.0;
   out_653094641834631323[147] = 0.0;
   out_653094641834631323[148] = 0.0;
   out_653094641834631323[149] = 0.0;
   out_653094641834631323[150] = 0.0;
   out_653094641834631323[151] = 0.0;
   out_653094641834631323[152] = 1.0;
   out_653094641834631323[153] = 0.0;
   out_653094641834631323[154] = 0.0;
   out_653094641834631323[155] = 0.0;
   out_653094641834631323[156] = 0.0;
   out_653094641834631323[157] = 0.0;
   out_653094641834631323[158] = 0.0;
   out_653094641834631323[159] = 0.0;
   out_653094641834631323[160] = 0.0;
   out_653094641834631323[161] = 0.0;
   out_653094641834631323[162] = 0.0;
   out_653094641834631323[163] = 0.0;
   out_653094641834631323[164] = 0.0;
   out_653094641834631323[165] = 0.0;
   out_653094641834631323[166] = 0.0;
   out_653094641834631323[167] = 0.0;
   out_653094641834631323[168] = 0.0;
   out_653094641834631323[169] = 0.0;
   out_653094641834631323[170] = 0.0;
   out_653094641834631323[171] = 1.0;
   out_653094641834631323[172] = 0.0;
   out_653094641834631323[173] = 0.0;
   out_653094641834631323[174] = 0.0;
   out_653094641834631323[175] = 0.0;
   out_653094641834631323[176] = 0.0;
   out_653094641834631323[177] = 0.0;
   out_653094641834631323[178] = 0.0;
   out_653094641834631323[179] = 0.0;
   out_653094641834631323[180] = 0.0;
   out_653094641834631323[181] = 0.0;
   out_653094641834631323[182] = 0.0;
   out_653094641834631323[183] = 0.0;
   out_653094641834631323[184] = 0.0;
   out_653094641834631323[185] = 0.0;
   out_653094641834631323[186] = 0.0;
   out_653094641834631323[187] = 0.0;
   out_653094641834631323[188] = 0.0;
   out_653094641834631323[189] = 0.0;
   out_653094641834631323[190] = 1.0;
   out_653094641834631323[191] = 0.0;
   out_653094641834631323[192] = 0.0;
   out_653094641834631323[193] = 0.0;
   out_653094641834631323[194] = 0.0;
   out_653094641834631323[195] = 0.0;
   out_653094641834631323[196] = 0.0;
   out_653094641834631323[197] = 0.0;
   out_653094641834631323[198] = 0.0;
   out_653094641834631323[199] = 0.0;
   out_653094641834631323[200] = 0.0;
   out_653094641834631323[201] = 0.0;
   out_653094641834631323[202] = 0.0;
   out_653094641834631323[203] = 0.0;
   out_653094641834631323[204] = 0.0;
   out_653094641834631323[205] = 0.0;
   out_653094641834631323[206] = 0.0;
   out_653094641834631323[207] = 0.0;
   out_653094641834631323[208] = 0.0;
   out_653094641834631323[209] = 1.0;
   out_653094641834631323[210] = 0.0;
   out_653094641834631323[211] = 0.0;
   out_653094641834631323[212] = 0.0;
   out_653094641834631323[213] = 0.0;
   out_653094641834631323[214] = 0.0;
   out_653094641834631323[215] = 0.0;
   out_653094641834631323[216] = 0.0;
   out_653094641834631323[217] = 0.0;
   out_653094641834631323[218] = 0.0;
   out_653094641834631323[219] = 0.0;
   out_653094641834631323[220] = 0.0;
   out_653094641834631323[221] = 0.0;
   out_653094641834631323[222] = 0.0;
   out_653094641834631323[223] = 0.0;
   out_653094641834631323[224] = 0.0;
   out_653094641834631323[225] = 0.0;
   out_653094641834631323[226] = 0.0;
   out_653094641834631323[227] = 0.0;
   out_653094641834631323[228] = 1.0;
   out_653094641834631323[229] = 0.0;
   out_653094641834631323[230] = 0.0;
   out_653094641834631323[231] = 0.0;
   out_653094641834631323[232] = 0.0;
   out_653094641834631323[233] = 0.0;
   out_653094641834631323[234] = 0.0;
   out_653094641834631323[235] = 0.0;
   out_653094641834631323[236] = 0.0;
   out_653094641834631323[237] = 0.0;
   out_653094641834631323[238] = 0.0;
   out_653094641834631323[239] = 0.0;
   out_653094641834631323[240] = 0.0;
   out_653094641834631323[241] = 0.0;
   out_653094641834631323[242] = 0.0;
   out_653094641834631323[243] = 0.0;
   out_653094641834631323[244] = 0.0;
   out_653094641834631323[245] = 0.0;
   out_653094641834631323[246] = 0.0;
   out_653094641834631323[247] = 1.0;
   out_653094641834631323[248] = 0.0;
   out_653094641834631323[249] = 0.0;
   out_653094641834631323[250] = 0.0;
   out_653094641834631323[251] = 0.0;
   out_653094641834631323[252] = 0.0;
   out_653094641834631323[253] = 0.0;
   out_653094641834631323[254] = 0.0;
   out_653094641834631323[255] = 0.0;
   out_653094641834631323[256] = 0.0;
   out_653094641834631323[257] = 0.0;
   out_653094641834631323[258] = 0.0;
   out_653094641834631323[259] = 0.0;
   out_653094641834631323[260] = 0.0;
   out_653094641834631323[261] = 0.0;
   out_653094641834631323[262] = 0.0;
   out_653094641834631323[263] = 0.0;
   out_653094641834631323[264] = 0.0;
   out_653094641834631323[265] = 0.0;
   out_653094641834631323[266] = 1.0;
   out_653094641834631323[267] = 0.0;
   out_653094641834631323[268] = 0.0;
   out_653094641834631323[269] = 0.0;
   out_653094641834631323[270] = 0.0;
   out_653094641834631323[271] = 0.0;
   out_653094641834631323[272] = 0.0;
   out_653094641834631323[273] = 0.0;
   out_653094641834631323[274] = 0.0;
   out_653094641834631323[275] = 0.0;
   out_653094641834631323[276] = 0.0;
   out_653094641834631323[277] = 0.0;
   out_653094641834631323[278] = 0.0;
   out_653094641834631323[279] = 0.0;
   out_653094641834631323[280] = 0.0;
   out_653094641834631323[281] = 0.0;
   out_653094641834631323[282] = 0.0;
   out_653094641834631323[283] = 0.0;
   out_653094641834631323[284] = 0.0;
   out_653094641834631323[285] = 1.0;
   out_653094641834631323[286] = 0.0;
   out_653094641834631323[287] = 0.0;
   out_653094641834631323[288] = 0.0;
   out_653094641834631323[289] = 0.0;
   out_653094641834631323[290] = 0.0;
   out_653094641834631323[291] = 0.0;
   out_653094641834631323[292] = 0.0;
   out_653094641834631323[293] = 0.0;
   out_653094641834631323[294] = 0.0;
   out_653094641834631323[295] = 0.0;
   out_653094641834631323[296] = 0.0;
   out_653094641834631323[297] = 0.0;
   out_653094641834631323[298] = 0.0;
   out_653094641834631323[299] = 0.0;
   out_653094641834631323[300] = 0.0;
   out_653094641834631323[301] = 0.0;
   out_653094641834631323[302] = 0.0;
   out_653094641834631323[303] = 0.0;
   out_653094641834631323[304] = 1.0;
   out_653094641834631323[305] = 0.0;
   out_653094641834631323[306] = 0.0;
   out_653094641834631323[307] = 0.0;
   out_653094641834631323[308] = 0.0;
   out_653094641834631323[309] = 0.0;
   out_653094641834631323[310] = 0.0;
   out_653094641834631323[311] = 0.0;
   out_653094641834631323[312] = 0.0;
   out_653094641834631323[313] = 0.0;
   out_653094641834631323[314] = 0.0;
   out_653094641834631323[315] = 0.0;
   out_653094641834631323[316] = 0.0;
   out_653094641834631323[317] = 0.0;
   out_653094641834631323[318] = 0.0;
   out_653094641834631323[319] = 0.0;
   out_653094641834631323[320] = 0.0;
   out_653094641834631323[321] = 0.0;
   out_653094641834631323[322] = 0.0;
   out_653094641834631323[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5955110383788875610) {
   out_5955110383788875610[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5955110383788875610[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5955110383788875610[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5955110383788875610[3] = dt*state[12] + state[3];
   out_5955110383788875610[4] = dt*state[13] + state[4];
   out_5955110383788875610[5] = dt*state[14] + state[5];
   out_5955110383788875610[6] = state[6];
   out_5955110383788875610[7] = state[7];
   out_5955110383788875610[8] = state[8];
   out_5955110383788875610[9] = state[9];
   out_5955110383788875610[10] = state[10];
   out_5955110383788875610[11] = state[11];
   out_5955110383788875610[12] = state[12];
   out_5955110383788875610[13] = state[13];
   out_5955110383788875610[14] = state[14];
   out_5955110383788875610[15] = state[15];
   out_5955110383788875610[16] = state[16];
   out_5955110383788875610[17] = state[17];
}
void F_fun(double *state, double dt, double *out_3374367099061520939) {
   out_3374367099061520939[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3374367099061520939[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3374367099061520939[2] = 0;
   out_3374367099061520939[3] = 0;
   out_3374367099061520939[4] = 0;
   out_3374367099061520939[5] = 0;
   out_3374367099061520939[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3374367099061520939[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3374367099061520939[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_3374367099061520939[9] = 0;
   out_3374367099061520939[10] = 0;
   out_3374367099061520939[11] = 0;
   out_3374367099061520939[12] = 0;
   out_3374367099061520939[13] = 0;
   out_3374367099061520939[14] = 0;
   out_3374367099061520939[15] = 0;
   out_3374367099061520939[16] = 0;
   out_3374367099061520939[17] = 0;
   out_3374367099061520939[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3374367099061520939[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3374367099061520939[20] = 0;
   out_3374367099061520939[21] = 0;
   out_3374367099061520939[22] = 0;
   out_3374367099061520939[23] = 0;
   out_3374367099061520939[24] = 0;
   out_3374367099061520939[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3374367099061520939[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_3374367099061520939[27] = 0;
   out_3374367099061520939[28] = 0;
   out_3374367099061520939[29] = 0;
   out_3374367099061520939[30] = 0;
   out_3374367099061520939[31] = 0;
   out_3374367099061520939[32] = 0;
   out_3374367099061520939[33] = 0;
   out_3374367099061520939[34] = 0;
   out_3374367099061520939[35] = 0;
   out_3374367099061520939[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3374367099061520939[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3374367099061520939[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3374367099061520939[39] = 0;
   out_3374367099061520939[40] = 0;
   out_3374367099061520939[41] = 0;
   out_3374367099061520939[42] = 0;
   out_3374367099061520939[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3374367099061520939[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_3374367099061520939[45] = 0;
   out_3374367099061520939[46] = 0;
   out_3374367099061520939[47] = 0;
   out_3374367099061520939[48] = 0;
   out_3374367099061520939[49] = 0;
   out_3374367099061520939[50] = 0;
   out_3374367099061520939[51] = 0;
   out_3374367099061520939[52] = 0;
   out_3374367099061520939[53] = 0;
   out_3374367099061520939[54] = 0;
   out_3374367099061520939[55] = 0;
   out_3374367099061520939[56] = 0;
   out_3374367099061520939[57] = 1;
   out_3374367099061520939[58] = 0;
   out_3374367099061520939[59] = 0;
   out_3374367099061520939[60] = 0;
   out_3374367099061520939[61] = 0;
   out_3374367099061520939[62] = 0;
   out_3374367099061520939[63] = 0;
   out_3374367099061520939[64] = 0;
   out_3374367099061520939[65] = 0;
   out_3374367099061520939[66] = dt;
   out_3374367099061520939[67] = 0;
   out_3374367099061520939[68] = 0;
   out_3374367099061520939[69] = 0;
   out_3374367099061520939[70] = 0;
   out_3374367099061520939[71] = 0;
   out_3374367099061520939[72] = 0;
   out_3374367099061520939[73] = 0;
   out_3374367099061520939[74] = 0;
   out_3374367099061520939[75] = 0;
   out_3374367099061520939[76] = 1;
   out_3374367099061520939[77] = 0;
   out_3374367099061520939[78] = 0;
   out_3374367099061520939[79] = 0;
   out_3374367099061520939[80] = 0;
   out_3374367099061520939[81] = 0;
   out_3374367099061520939[82] = 0;
   out_3374367099061520939[83] = 0;
   out_3374367099061520939[84] = 0;
   out_3374367099061520939[85] = dt;
   out_3374367099061520939[86] = 0;
   out_3374367099061520939[87] = 0;
   out_3374367099061520939[88] = 0;
   out_3374367099061520939[89] = 0;
   out_3374367099061520939[90] = 0;
   out_3374367099061520939[91] = 0;
   out_3374367099061520939[92] = 0;
   out_3374367099061520939[93] = 0;
   out_3374367099061520939[94] = 0;
   out_3374367099061520939[95] = 1;
   out_3374367099061520939[96] = 0;
   out_3374367099061520939[97] = 0;
   out_3374367099061520939[98] = 0;
   out_3374367099061520939[99] = 0;
   out_3374367099061520939[100] = 0;
   out_3374367099061520939[101] = 0;
   out_3374367099061520939[102] = 0;
   out_3374367099061520939[103] = 0;
   out_3374367099061520939[104] = dt;
   out_3374367099061520939[105] = 0;
   out_3374367099061520939[106] = 0;
   out_3374367099061520939[107] = 0;
   out_3374367099061520939[108] = 0;
   out_3374367099061520939[109] = 0;
   out_3374367099061520939[110] = 0;
   out_3374367099061520939[111] = 0;
   out_3374367099061520939[112] = 0;
   out_3374367099061520939[113] = 0;
   out_3374367099061520939[114] = 1;
   out_3374367099061520939[115] = 0;
   out_3374367099061520939[116] = 0;
   out_3374367099061520939[117] = 0;
   out_3374367099061520939[118] = 0;
   out_3374367099061520939[119] = 0;
   out_3374367099061520939[120] = 0;
   out_3374367099061520939[121] = 0;
   out_3374367099061520939[122] = 0;
   out_3374367099061520939[123] = 0;
   out_3374367099061520939[124] = 0;
   out_3374367099061520939[125] = 0;
   out_3374367099061520939[126] = 0;
   out_3374367099061520939[127] = 0;
   out_3374367099061520939[128] = 0;
   out_3374367099061520939[129] = 0;
   out_3374367099061520939[130] = 0;
   out_3374367099061520939[131] = 0;
   out_3374367099061520939[132] = 0;
   out_3374367099061520939[133] = 1;
   out_3374367099061520939[134] = 0;
   out_3374367099061520939[135] = 0;
   out_3374367099061520939[136] = 0;
   out_3374367099061520939[137] = 0;
   out_3374367099061520939[138] = 0;
   out_3374367099061520939[139] = 0;
   out_3374367099061520939[140] = 0;
   out_3374367099061520939[141] = 0;
   out_3374367099061520939[142] = 0;
   out_3374367099061520939[143] = 0;
   out_3374367099061520939[144] = 0;
   out_3374367099061520939[145] = 0;
   out_3374367099061520939[146] = 0;
   out_3374367099061520939[147] = 0;
   out_3374367099061520939[148] = 0;
   out_3374367099061520939[149] = 0;
   out_3374367099061520939[150] = 0;
   out_3374367099061520939[151] = 0;
   out_3374367099061520939[152] = 1;
   out_3374367099061520939[153] = 0;
   out_3374367099061520939[154] = 0;
   out_3374367099061520939[155] = 0;
   out_3374367099061520939[156] = 0;
   out_3374367099061520939[157] = 0;
   out_3374367099061520939[158] = 0;
   out_3374367099061520939[159] = 0;
   out_3374367099061520939[160] = 0;
   out_3374367099061520939[161] = 0;
   out_3374367099061520939[162] = 0;
   out_3374367099061520939[163] = 0;
   out_3374367099061520939[164] = 0;
   out_3374367099061520939[165] = 0;
   out_3374367099061520939[166] = 0;
   out_3374367099061520939[167] = 0;
   out_3374367099061520939[168] = 0;
   out_3374367099061520939[169] = 0;
   out_3374367099061520939[170] = 0;
   out_3374367099061520939[171] = 1;
   out_3374367099061520939[172] = 0;
   out_3374367099061520939[173] = 0;
   out_3374367099061520939[174] = 0;
   out_3374367099061520939[175] = 0;
   out_3374367099061520939[176] = 0;
   out_3374367099061520939[177] = 0;
   out_3374367099061520939[178] = 0;
   out_3374367099061520939[179] = 0;
   out_3374367099061520939[180] = 0;
   out_3374367099061520939[181] = 0;
   out_3374367099061520939[182] = 0;
   out_3374367099061520939[183] = 0;
   out_3374367099061520939[184] = 0;
   out_3374367099061520939[185] = 0;
   out_3374367099061520939[186] = 0;
   out_3374367099061520939[187] = 0;
   out_3374367099061520939[188] = 0;
   out_3374367099061520939[189] = 0;
   out_3374367099061520939[190] = 1;
   out_3374367099061520939[191] = 0;
   out_3374367099061520939[192] = 0;
   out_3374367099061520939[193] = 0;
   out_3374367099061520939[194] = 0;
   out_3374367099061520939[195] = 0;
   out_3374367099061520939[196] = 0;
   out_3374367099061520939[197] = 0;
   out_3374367099061520939[198] = 0;
   out_3374367099061520939[199] = 0;
   out_3374367099061520939[200] = 0;
   out_3374367099061520939[201] = 0;
   out_3374367099061520939[202] = 0;
   out_3374367099061520939[203] = 0;
   out_3374367099061520939[204] = 0;
   out_3374367099061520939[205] = 0;
   out_3374367099061520939[206] = 0;
   out_3374367099061520939[207] = 0;
   out_3374367099061520939[208] = 0;
   out_3374367099061520939[209] = 1;
   out_3374367099061520939[210] = 0;
   out_3374367099061520939[211] = 0;
   out_3374367099061520939[212] = 0;
   out_3374367099061520939[213] = 0;
   out_3374367099061520939[214] = 0;
   out_3374367099061520939[215] = 0;
   out_3374367099061520939[216] = 0;
   out_3374367099061520939[217] = 0;
   out_3374367099061520939[218] = 0;
   out_3374367099061520939[219] = 0;
   out_3374367099061520939[220] = 0;
   out_3374367099061520939[221] = 0;
   out_3374367099061520939[222] = 0;
   out_3374367099061520939[223] = 0;
   out_3374367099061520939[224] = 0;
   out_3374367099061520939[225] = 0;
   out_3374367099061520939[226] = 0;
   out_3374367099061520939[227] = 0;
   out_3374367099061520939[228] = 1;
   out_3374367099061520939[229] = 0;
   out_3374367099061520939[230] = 0;
   out_3374367099061520939[231] = 0;
   out_3374367099061520939[232] = 0;
   out_3374367099061520939[233] = 0;
   out_3374367099061520939[234] = 0;
   out_3374367099061520939[235] = 0;
   out_3374367099061520939[236] = 0;
   out_3374367099061520939[237] = 0;
   out_3374367099061520939[238] = 0;
   out_3374367099061520939[239] = 0;
   out_3374367099061520939[240] = 0;
   out_3374367099061520939[241] = 0;
   out_3374367099061520939[242] = 0;
   out_3374367099061520939[243] = 0;
   out_3374367099061520939[244] = 0;
   out_3374367099061520939[245] = 0;
   out_3374367099061520939[246] = 0;
   out_3374367099061520939[247] = 1;
   out_3374367099061520939[248] = 0;
   out_3374367099061520939[249] = 0;
   out_3374367099061520939[250] = 0;
   out_3374367099061520939[251] = 0;
   out_3374367099061520939[252] = 0;
   out_3374367099061520939[253] = 0;
   out_3374367099061520939[254] = 0;
   out_3374367099061520939[255] = 0;
   out_3374367099061520939[256] = 0;
   out_3374367099061520939[257] = 0;
   out_3374367099061520939[258] = 0;
   out_3374367099061520939[259] = 0;
   out_3374367099061520939[260] = 0;
   out_3374367099061520939[261] = 0;
   out_3374367099061520939[262] = 0;
   out_3374367099061520939[263] = 0;
   out_3374367099061520939[264] = 0;
   out_3374367099061520939[265] = 0;
   out_3374367099061520939[266] = 1;
   out_3374367099061520939[267] = 0;
   out_3374367099061520939[268] = 0;
   out_3374367099061520939[269] = 0;
   out_3374367099061520939[270] = 0;
   out_3374367099061520939[271] = 0;
   out_3374367099061520939[272] = 0;
   out_3374367099061520939[273] = 0;
   out_3374367099061520939[274] = 0;
   out_3374367099061520939[275] = 0;
   out_3374367099061520939[276] = 0;
   out_3374367099061520939[277] = 0;
   out_3374367099061520939[278] = 0;
   out_3374367099061520939[279] = 0;
   out_3374367099061520939[280] = 0;
   out_3374367099061520939[281] = 0;
   out_3374367099061520939[282] = 0;
   out_3374367099061520939[283] = 0;
   out_3374367099061520939[284] = 0;
   out_3374367099061520939[285] = 1;
   out_3374367099061520939[286] = 0;
   out_3374367099061520939[287] = 0;
   out_3374367099061520939[288] = 0;
   out_3374367099061520939[289] = 0;
   out_3374367099061520939[290] = 0;
   out_3374367099061520939[291] = 0;
   out_3374367099061520939[292] = 0;
   out_3374367099061520939[293] = 0;
   out_3374367099061520939[294] = 0;
   out_3374367099061520939[295] = 0;
   out_3374367099061520939[296] = 0;
   out_3374367099061520939[297] = 0;
   out_3374367099061520939[298] = 0;
   out_3374367099061520939[299] = 0;
   out_3374367099061520939[300] = 0;
   out_3374367099061520939[301] = 0;
   out_3374367099061520939[302] = 0;
   out_3374367099061520939[303] = 0;
   out_3374367099061520939[304] = 1;
   out_3374367099061520939[305] = 0;
   out_3374367099061520939[306] = 0;
   out_3374367099061520939[307] = 0;
   out_3374367099061520939[308] = 0;
   out_3374367099061520939[309] = 0;
   out_3374367099061520939[310] = 0;
   out_3374367099061520939[311] = 0;
   out_3374367099061520939[312] = 0;
   out_3374367099061520939[313] = 0;
   out_3374367099061520939[314] = 0;
   out_3374367099061520939[315] = 0;
   out_3374367099061520939[316] = 0;
   out_3374367099061520939[317] = 0;
   out_3374367099061520939[318] = 0;
   out_3374367099061520939[319] = 0;
   out_3374367099061520939[320] = 0;
   out_3374367099061520939[321] = 0;
   out_3374367099061520939[322] = 0;
   out_3374367099061520939[323] = 1;
}
void h_4(double *state, double *unused, double *out_583201360619966174) {
   out_583201360619966174[0] = state[6] + state[9];
   out_583201360619966174[1] = state[7] + state[10];
   out_583201360619966174[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_402417908502924402) {
   out_402417908502924402[0] = 0;
   out_402417908502924402[1] = 0;
   out_402417908502924402[2] = 0;
   out_402417908502924402[3] = 0;
   out_402417908502924402[4] = 0;
   out_402417908502924402[5] = 0;
   out_402417908502924402[6] = 1;
   out_402417908502924402[7] = 0;
   out_402417908502924402[8] = 0;
   out_402417908502924402[9] = 1;
   out_402417908502924402[10] = 0;
   out_402417908502924402[11] = 0;
   out_402417908502924402[12] = 0;
   out_402417908502924402[13] = 0;
   out_402417908502924402[14] = 0;
   out_402417908502924402[15] = 0;
   out_402417908502924402[16] = 0;
   out_402417908502924402[17] = 0;
   out_402417908502924402[18] = 0;
   out_402417908502924402[19] = 0;
   out_402417908502924402[20] = 0;
   out_402417908502924402[21] = 0;
   out_402417908502924402[22] = 0;
   out_402417908502924402[23] = 0;
   out_402417908502924402[24] = 0;
   out_402417908502924402[25] = 1;
   out_402417908502924402[26] = 0;
   out_402417908502924402[27] = 0;
   out_402417908502924402[28] = 1;
   out_402417908502924402[29] = 0;
   out_402417908502924402[30] = 0;
   out_402417908502924402[31] = 0;
   out_402417908502924402[32] = 0;
   out_402417908502924402[33] = 0;
   out_402417908502924402[34] = 0;
   out_402417908502924402[35] = 0;
   out_402417908502924402[36] = 0;
   out_402417908502924402[37] = 0;
   out_402417908502924402[38] = 0;
   out_402417908502924402[39] = 0;
   out_402417908502924402[40] = 0;
   out_402417908502924402[41] = 0;
   out_402417908502924402[42] = 0;
   out_402417908502924402[43] = 0;
   out_402417908502924402[44] = 1;
   out_402417908502924402[45] = 0;
   out_402417908502924402[46] = 0;
   out_402417908502924402[47] = 1;
   out_402417908502924402[48] = 0;
   out_402417908502924402[49] = 0;
   out_402417908502924402[50] = 0;
   out_402417908502924402[51] = 0;
   out_402417908502924402[52] = 0;
   out_402417908502924402[53] = 0;
}
void h_10(double *state, double *unused, double *out_356753245810915962) {
   out_356753245810915962[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_356753245810915962[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_356753245810915962[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7727584574864679993) {
   out_7727584574864679993[0] = 0;
   out_7727584574864679993[1] = 9.8100000000000005*cos(state[1]);
   out_7727584574864679993[2] = 0;
   out_7727584574864679993[3] = 0;
   out_7727584574864679993[4] = -state[8];
   out_7727584574864679993[5] = state[7];
   out_7727584574864679993[6] = 0;
   out_7727584574864679993[7] = state[5];
   out_7727584574864679993[8] = -state[4];
   out_7727584574864679993[9] = 0;
   out_7727584574864679993[10] = 0;
   out_7727584574864679993[11] = 0;
   out_7727584574864679993[12] = 1;
   out_7727584574864679993[13] = 0;
   out_7727584574864679993[14] = 0;
   out_7727584574864679993[15] = 1;
   out_7727584574864679993[16] = 0;
   out_7727584574864679993[17] = 0;
   out_7727584574864679993[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7727584574864679993[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7727584574864679993[20] = 0;
   out_7727584574864679993[21] = state[8];
   out_7727584574864679993[22] = 0;
   out_7727584574864679993[23] = -state[6];
   out_7727584574864679993[24] = -state[5];
   out_7727584574864679993[25] = 0;
   out_7727584574864679993[26] = state[3];
   out_7727584574864679993[27] = 0;
   out_7727584574864679993[28] = 0;
   out_7727584574864679993[29] = 0;
   out_7727584574864679993[30] = 0;
   out_7727584574864679993[31] = 1;
   out_7727584574864679993[32] = 0;
   out_7727584574864679993[33] = 0;
   out_7727584574864679993[34] = 1;
   out_7727584574864679993[35] = 0;
   out_7727584574864679993[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7727584574864679993[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7727584574864679993[38] = 0;
   out_7727584574864679993[39] = -state[7];
   out_7727584574864679993[40] = state[6];
   out_7727584574864679993[41] = 0;
   out_7727584574864679993[42] = state[4];
   out_7727584574864679993[43] = -state[3];
   out_7727584574864679993[44] = 0;
   out_7727584574864679993[45] = 0;
   out_7727584574864679993[46] = 0;
   out_7727584574864679993[47] = 0;
   out_7727584574864679993[48] = 0;
   out_7727584574864679993[49] = 0;
   out_7727584574864679993[50] = 1;
   out_7727584574864679993[51] = 0;
   out_7727584574864679993[52] = 0;
   out_7727584574864679993[53] = 1;
}
void h_13(double *state, double *unused, double *out_1340717926179505345) {
   out_1340717926179505345[0] = state[3];
   out_1340717926179505345[1] = state[4];
   out_1340717926179505345[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7208213299813776527) {
   out_7208213299813776527[0] = 0;
   out_7208213299813776527[1] = 0;
   out_7208213299813776527[2] = 0;
   out_7208213299813776527[3] = 1;
   out_7208213299813776527[4] = 0;
   out_7208213299813776527[5] = 0;
   out_7208213299813776527[6] = 0;
   out_7208213299813776527[7] = 0;
   out_7208213299813776527[8] = 0;
   out_7208213299813776527[9] = 0;
   out_7208213299813776527[10] = 0;
   out_7208213299813776527[11] = 0;
   out_7208213299813776527[12] = 0;
   out_7208213299813776527[13] = 0;
   out_7208213299813776527[14] = 0;
   out_7208213299813776527[15] = 0;
   out_7208213299813776527[16] = 0;
   out_7208213299813776527[17] = 0;
   out_7208213299813776527[18] = 0;
   out_7208213299813776527[19] = 0;
   out_7208213299813776527[20] = 0;
   out_7208213299813776527[21] = 0;
   out_7208213299813776527[22] = 1;
   out_7208213299813776527[23] = 0;
   out_7208213299813776527[24] = 0;
   out_7208213299813776527[25] = 0;
   out_7208213299813776527[26] = 0;
   out_7208213299813776527[27] = 0;
   out_7208213299813776527[28] = 0;
   out_7208213299813776527[29] = 0;
   out_7208213299813776527[30] = 0;
   out_7208213299813776527[31] = 0;
   out_7208213299813776527[32] = 0;
   out_7208213299813776527[33] = 0;
   out_7208213299813776527[34] = 0;
   out_7208213299813776527[35] = 0;
   out_7208213299813776527[36] = 0;
   out_7208213299813776527[37] = 0;
   out_7208213299813776527[38] = 0;
   out_7208213299813776527[39] = 0;
   out_7208213299813776527[40] = 0;
   out_7208213299813776527[41] = 1;
   out_7208213299813776527[42] = 0;
   out_7208213299813776527[43] = 0;
   out_7208213299813776527[44] = 0;
   out_7208213299813776527[45] = 0;
   out_7208213299813776527[46] = 0;
   out_7208213299813776527[47] = 0;
   out_7208213299813776527[48] = 0;
   out_7208213299813776527[49] = 0;
   out_7208213299813776527[50] = 0;
   out_7208213299813776527[51] = 0;
   out_7208213299813776527[52] = 0;
   out_7208213299813776527[53] = 0;
}
void h_14(double *state, double *unused, double *out_4852912044053324854) {
   out_4852912044053324854[0] = state[6];
   out_4852912044053324854[1] = state[7];
   out_4852912044053324854[2] = state[8];
}
void H_14(double *state, double *unused, double *out_3560822947836560127) {
   out_3560822947836560127[0] = 0;
   out_3560822947836560127[1] = 0;
   out_3560822947836560127[2] = 0;
   out_3560822947836560127[3] = 0;
   out_3560822947836560127[4] = 0;
   out_3560822947836560127[5] = 0;
   out_3560822947836560127[6] = 1;
   out_3560822947836560127[7] = 0;
   out_3560822947836560127[8] = 0;
   out_3560822947836560127[9] = 0;
   out_3560822947836560127[10] = 0;
   out_3560822947836560127[11] = 0;
   out_3560822947836560127[12] = 0;
   out_3560822947836560127[13] = 0;
   out_3560822947836560127[14] = 0;
   out_3560822947836560127[15] = 0;
   out_3560822947836560127[16] = 0;
   out_3560822947836560127[17] = 0;
   out_3560822947836560127[18] = 0;
   out_3560822947836560127[19] = 0;
   out_3560822947836560127[20] = 0;
   out_3560822947836560127[21] = 0;
   out_3560822947836560127[22] = 0;
   out_3560822947836560127[23] = 0;
   out_3560822947836560127[24] = 0;
   out_3560822947836560127[25] = 1;
   out_3560822947836560127[26] = 0;
   out_3560822947836560127[27] = 0;
   out_3560822947836560127[28] = 0;
   out_3560822947836560127[29] = 0;
   out_3560822947836560127[30] = 0;
   out_3560822947836560127[31] = 0;
   out_3560822947836560127[32] = 0;
   out_3560822947836560127[33] = 0;
   out_3560822947836560127[34] = 0;
   out_3560822947836560127[35] = 0;
   out_3560822947836560127[36] = 0;
   out_3560822947836560127[37] = 0;
   out_3560822947836560127[38] = 0;
   out_3560822947836560127[39] = 0;
   out_3560822947836560127[40] = 0;
   out_3560822947836560127[41] = 0;
   out_3560822947836560127[42] = 0;
   out_3560822947836560127[43] = 0;
   out_3560822947836560127[44] = 1;
   out_3560822947836560127[45] = 0;
   out_3560822947836560127[46] = 0;
   out_3560822947836560127[47] = 0;
   out_3560822947836560127[48] = 0;
   out_3560822947836560127[49] = 0;
   out_3560822947836560127[50] = 0;
   out_3560822947836560127[51] = 0;
   out_3560822947836560127[52] = 0;
   out_3560822947836560127[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_7992688260990922493) {
  err_fun(nom_x, delta_x, out_7992688260990922493);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5809721741941332225) {
  inv_err_fun(nom_x, true_x, out_5809721741941332225);
}
void pose_H_mod_fun(double *state, double *out_653094641834631323) {
  H_mod_fun(state, out_653094641834631323);
}
void pose_f_fun(double *state, double dt, double *out_5955110383788875610) {
  f_fun(state,  dt, out_5955110383788875610);
}
void pose_F_fun(double *state, double dt, double *out_3374367099061520939) {
  F_fun(state,  dt, out_3374367099061520939);
}
void pose_h_4(double *state, double *unused, double *out_583201360619966174) {
  h_4(state, unused, out_583201360619966174);
}
void pose_H_4(double *state, double *unused, double *out_402417908502924402) {
  H_4(state, unused, out_402417908502924402);
}
void pose_h_10(double *state, double *unused, double *out_356753245810915962) {
  h_10(state, unused, out_356753245810915962);
}
void pose_H_10(double *state, double *unused, double *out_7727584574864679993) {
  H_10(state, unused, out_7727584574864679993);
}
void pose_h_13(double *state, double *unused, double *out_1340717926179505345) {
  h_13(state, unused, out_1340717926179505345);
}
void pose_H_13(double *state, double *unused, double *out_7208213299813776527) {
  H_13(state, unused, out_7208213299813776527);
}
void pose_h_14(double *state, double *unused, double *out_4852912044053324854) {
  h_14(state, unused, out_4852912044053324854);
}
void pose_H_14(double *state, double *unused, double *out_3560822947836560127) {
  H_14(state, unused, out_3560822947836560127);
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
