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
void err_fun(double *nom_x, double *delta_x, double *out_3592422939216669323) {
   out_3592422939216669323[0] = delta_x[0] + nom_x[0];
   out_3592422939216669323[1] = delta_x[1] + nom_x[1];
   out_3592422939216669323[2] = delta_x[2] + nom_x[2];
   out_3592422939216669323[3] = delta_x[3] + nom_x[3];
   out_3592422939216669323[4] = delta_x[4] + nom_x[4];
   out_3592422939216669323[5] = delta_x[5] + nom_x[5];
   out_3592422939216669323[6] = delta_x[6] + nom_x[6];
   out_3592422939216669323[7] = delta_x[7] + nom_x[7];
   out_3592422939216669323[8] = delta_x[8] + nom_x[8];
   out_3592422939216669323[9] = delta_x[9] + nom_x[9];
   out_3592422939216669323[10] = delta_x[10] + nom_x[10];
   out_3592422939216669323[11] = delta_x[11] + nom_x[11];
   out_3592422939216669323[12] = delta_x[12] + nom_x[12];
   out_3592422939216669323[13] = delta_x[13] + nom_x[13];
   out_3592422939216669323[14] = delta_x[14] + nom_x[14];
   out_3592422939216669323[15] = delta_x[15] + nom_x[15];
   out_3592422939216669323[16] = delta_x[16] + nom_x[16];
   out_3592422939216669323[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6915701396310957140) {
   out_6915701396310957140[0] = -nom_x[0] + true_x[0];
   out_6915701396310957140[1] = -nom_x[1] + true_x[1];
   out_6915701396310957140[2] = -nom_x[2] + true_x[2];
   out_6915701396310957140[3] = -nom_x[3] + true_x[3];
   out_6915701396310957140[4] = -nom_x[4] + true_x[4];
   out_6915701396310957140[5] = -nom_x[5] + true_x[5];
   out_6915701396310957140[6] = -nom_x[6] + true_x[6];
   out_6915701396310957140[7] = -nom_x[7] + true_x[7];
   out_6915701396310957140[8] = -nom_x[8] + true_x[8];
   out_6915701396310957140[9] = -nom_x[9] + true_x[9];
   out_6915701396310957140[10] = -nom_x[10] + true_x[10];
   out_6915701396310957140[11] = -nom_x[11] + true_x[11];
   out_6915701396310957140[12] = -nom_x[12] + true_x[12];
   out_6915701396310957140[13] = -nom_x[13] + true_x[13];
   out_6915701396310957140[14] = -nom_x[14] + true_x[14];
   out_6915701396310957140[15] = -nom_x[15] + true_x[15];
   out_6915701396310957140[16] = -nom_x[16] + true_x[16];
   out_6915701396310957140[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3743404816978430653) {
   out_3743404816978430653[0] = 1.0;
   out_3743404816978430653[1] = 0.0;
   out_3743404816978430653[2] = 0.0;
   out_3743404816978430653[3] = 0.0;
   out_3743404816978430653[4] = 0.0;
   out_3743404816978430653[5] = 0.0;
   out_3743404816978430653[6] = 0.0;
   out_3743404816978430653[7] = 0.0;
   out_3743404816978430653[8] = 0.0;
   out_3743404816978430653[9] = 0.0;
   out_3743404816978430653[10] = 0.0;
   out_3743404816978430653[11] = 0.0;
   out_3743404816978430653[12] = 0.0;
   out_3743404816978430653[13] = 0.0;
   out_3743404816978430653[14] = 0.0;
   out_3743404816978430653[15] = 0.0;
   out_3743404816978430653[16] = 0.0;
   out_3743404816978430653[17] = 0.0;
   out_3743404816978430653[18] = 0.0;
   out_3743404816978430653[19] = 1.0;
   out_3743404816978430653[20] = 0.0;
   out_3743404816978430653[21] = 0.0;
   out_3743404816978430653[22] = 0.0;
   out_3743404816978430653[23] = 0.0;
   out_3743404816978430653[24] = 0.0;
   out_3743404816978430653[25] = 0.0;
   out_3743404816978430653[26] = 0.0;
   out_3743404816978430653[27] = 0.0;
   out_3743404816978430653[28] = 0.0;
   out_3743404816978430653[29] = 0.0;
   out_3743404816978430653[30] = 0.0;
   out_3743404816978430653[31] = 0.0;
   out_3743404816978430653[32] = 0.0;
   out_3743404816978430653[33] = 0.0;
   out_3743404816978430653[34] = 0.0;
   out_3743404816978430653[35] = 0.0;
   out_3743404816978430653[36] = 0.0;
   out_3743404816978430653[37] = 0.0;
   out_3743404816978430653[38] = 1.0;
   out_3743404816978430653[39] = 0.0;
   out_3743404816978430653[40] = 0.0;
   out_3743404816978430653[41] = 0.0;
   out_3743404816978430653[42] = 0.0;
   out_3743404816978430653[43] = 0.0;
   out_3743404816978430653[44] = 0.0;
   out_3743404816978430653[45] = 0.0;
   out_3743404816978430653[46] = 0.0;
   out_3743404816978430653[47] = 0.0;
   out_3743404816978430653[48] = 0.0;
   out_3743404816978430653[49] = 0.0;
   out_3743404816978430653[50] = 0.0;
   out_3743404816978430653[51] = 0.0;
   out_3743404816978430653[52] = 0.0;
   out_3743404816978430653[53] = 0.0;
   out_3743404816978430653[54] = 0.0;
   out_3743404816978430653[55] = 0.0;
   out_3743404816978430653[56] = 0.0;
   out_3743404816978430653[57] = 1.0;
   out_3743404816978430653[58] = 0.0;
   out_3743404816978430653[59] = 0.0;
   out_3743404816978430653[60] = 0.0;
   out_3743404816978430653[61] = 0.0;
   out_3743404816978430653[62] = 0.0;
   out_3743404816978430653[63] = 0.0;
   out_3743404816978430653[64] = 0.0;
   out_3743404816978430653[65] = 0.0;
   out_3743404816978430653[66] = 0.0;
   out_3743404816978430653[67] = 0.0;
   out_3743404816978430653[68] = 0.0;
   out_3743404816978430653[69] = 0.0;
   out_3743404816978430653[70] = 0.0;
   out_3743404816978430653[71] = 0.0;
   out_3743404816978430653[72] = 0.0;
   out_3743404816978430653[73] = 0.0;
   out_3743404816978430653[74] = 0.0;
   out_3743404816978430653[75] = 0.0;
   out_3743404816978430653[76] = 1.0;
   out_3743404816978430653[77] = 0.0;
   out_3743404816978430653[78] = 0.0;
   out_3743404816978430653[79] = 0.0;
   out_3743404816978430653[80] = 0.0;
   out_3743404816978430653[81] = 0.0;
   out_3743404816978430653[82] = 0.0;
   out_3743404816978430653[83] = 0.0;
   out_3743404816978430653[84] = 0.0;
   out_3743404816978430653[85] = 0.0;
   out_3743404816978430653[86] = 0.0;
   out_3743404816978430653[87] = 0.0;
   out_3743404816978430653[88] = 0.0;
   out_3743404816978430653[89] = 0.0;
   out_3743404816978430653[90] = 0.0;
   out_3743404816978430653[91] = 0.0;
   out_3743404816978430653[92] = 0.0;
   out_3743404816978430653[93] = 0.0;
   out_3743404816978430653[94] = 0.0;
   out_3743404816978430653[95] = 1.0;
   out_3743404816978430653[96] = 0.0;
   out_3743404816978430653[97] = 0.0;
   out_3743404816978430653[98] = 0.0;
   out_3743404816978430653[99] = 0.0;
   out_3743404816978430653[100] = 0.0;
   out_3743404816978430653[101] = 0.0;
   out_3743404816978430653[102] = 0.0;
   out_3743404816978430653[103] = 0.0;
   out_3743404816978430653[104] = 0.0;
   out_3743404816978430653[105] = 0.0;
   out_3743404816978430653[106] = 0.0;
   out_3743404816978430653[107] = 0.0;
   out_3743404816978430653[108] = 0.0;
   out_3743404816978430653[109] = 0.0;
   out_3743404816978430653[110] = 0.0;
   out_3743404816978430653[111] = 0.0;
   out_3743404816978430653[112] = 0.0;
   out_3743404816978430653[113] = 0.0;
   out_3743404816978430653[114] = 1.0;
   out_3743404816978430653[115] = 0.0;
   out_3743404816978430653[116] = 0.0;
   out_3743404816978430653[117] = 0.0;
   out_3743404816978430653[118] = 0.0;
   out_3743404816978430653[119] = 0.0;
   out_3743404816978430653[120] = 0.0;
   out_3743404816978430653[121] = 0.0;
   out_3743404816978430653[122] = 0.0;
   out_3743404816978430653[123] = 0.0;
   out_3743404816978430653[124] = 0.0;
   out_3743404816978430653[125] = 0.0;
   out_3743404816978430653[126] = 0.0;
   out_3743404816978430653[127] = 0.0;
   out_3743404816978430653[128] = 0.0;
   out_3743404816978430653[129] = 0.0;
   out_3743404816978430653[130] = 0.0;
   out_3743404816978430653[131] = 0.0;
   out_3743404816978430653[132] = 0.0;
   out_3743404816978430653[133] = 1.0;
   out_3743404816978430653[134] = 0.0;
   out_3743404816978430653[135] = 0.0;
   out_3743404816978430653[136] = 0.0;
   out_3743404816978430653[137] = 0.0;
   out_3743404816978430653[138] = 0.0;
   out_3743404816978430653[139] = 0.0;
   out_3743404816978430653[140] = 0.0;
   out_3743404816978430653[141] = 0.0;
   out_3743404816978430653[142] = 0.0;
   out_3743404816978430653[143] = 0.0;
   out_3743404816978430653[144] = 0.0;
   out_3743404816978430653[145] = 0.0;
   out_3743404816978430653[146] = 0.0;
   out_3743404816978430653[147] = 0.0;
   out_3743404816978430653[148] = 0.0;
   out_3743404816978430653[149] = 0.0;
   out_3743404816978430653[150] = 0.0;
   out_3743404816978430653[151] = 0.0;
   out_3743404816978430653[152] = 1.0;
   out_3743404816978430653[153] = 0.0;
   out_3743404816978430653[154] = 0.0;
   out_3743404816978430653[155] = 0.0;
   out_3743404816978430653[156] = 0.0;
   out_3743404816978430653[157] = 0.0;
   out_3743404816978430653[158] = 0.0;
   out_3743404816978430653[159] = 0.0;
   out_3743404816978430653[160] = 0.0;
   out_3743404816978430653[161] = 0.0;
   out_3743404816978430653[162] = 0.0;
   out_3743404816978430653[163] = 0.0;
   out_3743404816978430653[164] = 0.0;
   out_3743404816978430653[165] = 0.0;
   out_3743404816978430653[166] = 0.0;
   out_3743404816978430653[167] = 0.0;
   out_3743404816978430653[168] = 0.0;
   out_3743404816978430653[169] = 0.0;
   out_3743404816978430653[170] = 0.0;
   out_3743404816978430653[171] = 1.0;
   out_3743404816978430653[172] = 0.0;
   out_3743404816978430653[173] = 0.0;
   out_3743404816978430653[174] = 0.0;
   out_3743404816978430653[175] = 0.0;
   out_3743404816978430653[176] = 0.0;
   out_3743404816978430653[177] = 0.0;
   out_3743404816978430653[178] = 0.0;
   out_3743404816978430653[179] = 0.0;
   out_3743404816978430653[180] = 0.0;
   out_3743404816978430653[181] = 0.0;
   out_3743404816978430653[182] = 0.0;
   out_3743404816978430653[183] = 0.0;
   out_3743404816978430653[184] = 0.0;
   out_3743404816978430653[185] = 0.0;
   out_3743404816978430653[186] = 0.0;
   out_3743404816978430653[187] = 0.0;
   out_3743404816978430653[188] = 0.0;
   out_3743404816978430653[189] = 0.0;
   out_3743404816978430653[190] = 1.0;
   out_3743404816978430653[191] = 0.0;
   out_3743404816978430653[192] = 0.0;
   out_3743404816978430653[193] = 0.0;
   out_3743404816978430653[194] = 0.0;
   out_3743404816978430653[195] = 0.0;
   out_3743404816978430653[196] = 0.0;
   out_3743404816978430653[197] = 0.0;
   out_3743404816978430653[198] = 0.0;
   out_3743404816978430653[199] = 0.0;
   out_3743404816978430653[200] = 0.0;
   out_3743404816978430653[201] = 0.0;
   out_3743404816978430653[202] = 0.0;
   out_3743404816978430653[203] = 0.0;
   out_3743404816978430653[204] = 0.0;
   out_3743404816978430653[205] = 0.0;
   out_3743404816978430653[206] = 0.0;
   out_3743404816978430653[207] = 0.0;
   out_3743404816978430653[208] = 0.0;
   out_3743404816978430653[209] = 1.0;
   out_3743404816978430653[210] = 0.0;
   out_3743404816978430653[211] = 0.0;
   out_3743404816978430653[212] = 0.0;
   out_3743404816978430653[213] = 0.0;
   out_3743404816978430653[214] = 0.0;
   out_3743404816978430653[215] = 0.0;
   out_3743404816978430653[216] = 0.0;
   out_3743404816978430653[217] = 0.0;
   out_3743404816978430653[218] = 0.0;
   out_3743404816978430653[219] = 0.0;
   out_3743404816978430653[220] = 0.0;
   out_3743404816978430653[221] = 0.0;
   out_3743404816978430653[222] = 0.0;
   out_3743404816978430653[223] = 0.0;
   out_3743404816978430653[224] = 0.0;
   out_3743404816978430653[225] = 0.0;
   out_3743404816978430653[226] = 0.0;
   out_3743404816978430653[227] = 0.0;
   out_3743404816978430653[228] = 1.0;
   out_3743404816978430653[229] = 0.0;
   out_3743404816978430653[230] = 0.0;
   out_3743404816978430653[231] = 0.0;
   out_3743404816978430653[232] = 0.0;
   out_3743404816978430653[233] = 0.0;
   out_3743404816978430653[234] = 0.0;
   out_3743404816978430653[235] = 0.0;
   out_3743404816978430653[236] = 0.0;
   out_3743404816978430653[237] = 0.0;
   out_3743404816978430653[238] = 0.0;
   out_3743404816978430653[239] = 0.0;
   out_3743404816978430653[240] = 0.0;
   out_3743404816978430653[241] = 0.0;
   out_3743404816978430653[242] = 0.0;
   out_3743404816978430653[243] = 0.0;
   out_3743404816978430653[244] = 0.0;
   out_3743404816978430653[245] = 0.0;
   out_3743404816978430653[246] = 0.0;
   out_3743404816978430653[247] = 1.0;
   out_3743404816978430653[248] = 0.0;
   out_3743404816978430653[249] = 0.0;
   out_3743404816978430653[250] = 0.0;
   out_3743404816978430653[251] = 0.0;
   out_3743404816978430653[252] = 0.0;
   out_3743404816978430653[253] = 0.0;
   out_3743404816978430653[254] = 0.0;
   out_3743404816978430653[255] = 0.0;
   out_3743404816978430653[256] = 0.0;
   out_3743404816978430653[257] = 0.0;
   out_3743404816978430653[258] = 0.0;
   out_3743404816978430653[259] = 0.0;
   out_3743404816978430653[260] = 0.0;
   out_3743404816978430653[261] = 0.0;
   out_3743404816978430653[262] = 0.0;
   out_3743404816978430653[263] = 0.0;
   out_3743404816978430653[264] = 0.0;
   out_3743404816978430653[265] = 0.0;
   out_3743404816978430653[266] = 1.0;
   out_3743404816978430653[267] = 0.0;
   out_3743404816978430653[268] = 0.0;
   out_3743404816978430653[269] = 0.0;
   out_3743404816978430653[270] = 0.0;
   out_3743404816978430653[271] = 0.0;
   out_3743404816978430653[272] = 0.0;
   out_3743404816978430653[273] = 0.0;
   out_3743404816978430653[274] = 0.0;
   out_3743404816978430653[275] = 0.0;
   out_3743404816978430653[276] = 0.0;
   out_3743404816978430653[277] = 0.0;
   out_3743404816978430653[278] = 0.0;
   out_3743404816978430653[279] = 0.0;
   out_3743404816978430653[280] = 0.0;
   out_3743404816978430653[281] = 0.0;
   out_3743404816978430653[282] = 0.0;
   out_3743404816978430653[283] = 0.0;
   out_3743404816978430653[284] = 0.0;
   out_3743404816978430653[285] = 1.0;
   out_3743404816978430653[286] = 0.0;
   out_3743404816978430653[287] = 0.0;
   out_3743404816978430653[288] = 0.0;
   out_3743404816978430653[289] = 0.0;
   out_3743404816978430653[290] = 0.0;
   out_3743404816978430653[291] = 0.0;
   out_3743404816978430653[292] = 0.0;
   out_3743404816978430653[293] = 0.0;
   out_3743404816978430653[294] = 0.0;
   out_3743404816978430653[295] = 0.0;
   out_3743404816978430653[296] = 0.0;
   out_3743404816978430653[297] = 0.0;
   out_3743404816978430653[298] = 0.0;
   out_3743404816978430653[299] = 0.0;
   out_3743404816978430653[300] = 0.0;
   out_3743404816978430653[301] = 0.0;
   out_3743404816978430653[302] = 0.0;
   out_3743404816978430653[303] = 0.0;
   out_3743404816978430653[304] = 1.0;
   out_3743404816978430653[305] = 0.0;
   out_3743404816978430653[306] = 0.0;
   out_3743404816978430653[307] = 0.0;
   out_3743404816978430653[308] = 0.0;
   out_3743404816978430653[309] = 0.0;
   out_3743404816978430653[310] = 0.0;
   out_3743404816978430653[311] = 0.0;
   out_3743404816978430653[312] = 0.0;
   out_3743404816978430653[313] = 0.0;
   out_3743404816978430653[314] = 0.0;
   out_3743404816978430653[315] = 0.0;
   out_3743404816978430653[316] = 0.0;
   out_3743404816978430653[317] = 0.0;
   out_3743404816978430653[318] = 0.0;
   out_3743404816978430653[319] = 0.0;
   out_3743404816978430653[320] = 0.0;
   out_3743404816978430653[321] = 0.0;
   out_3743404816978430653[322] = 0.0;
   out_3743404816978430653[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_971936760635752887) {
   out_971936760635752887[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_971936760635752887[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_971936760635752887[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_971936760635752887[3] = dt*state[12] + state[3];
   out_971936760635752887[4] = dt*state[13] + state[4];
   out_971936760635752887[5] = dt*state[14] + state[5];
   out_971936760635752887[6] = state[6];
   out_971936760635752887[7] = state[7];
   out_971936760635752887[8] = state[8];
   out_971936760635752887[9] = state[9];
   out_971936760635752887[10] = state[10];
   out_971936760635752887[11] = state[11];
   out_971936760635752887[12] = state[12];
   out_971936760635752887[13] = state[13];
   out_971936760635752887[14] = state[14];
   out_971936760635752887[15] = state[15];
   out_971936760635752887[16] = state[16];
   out_971936760635752887[17] = state[17];
}
void F_fun(double *state, double dt, double *out_5997582763311156755) {
   out_5997582763311156755[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5997582763311156755[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5997582763311156755[2] = 0;
   out_5997582763311156755[3] = 0;
   out_5997582763311156755[4] = 0;
   out_5997582763311156755[5] = 0;
   out_5997582763311156755[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5997582763311156755[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5997582763311156755[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_5997582763311156755[9] = 0;
   out_5997582763311156755[10] = 0;
   out_5997582763311156755[11] = 0;
   out_5997582763311156755[12] = 0;
   out_5997582763311156755[13] = 0;
   out_5997582763311156755[14] = 0;
   out_5997582763311156755[15] = 0;
   out_5997582763311156755[16] = 0;
   out_5997582763311156755[17] = 0;
   out_5997582763311156755[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5997582763311156755[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5997582763311156755[20] = 0;
   out_5997582763311156755[21] = 0;
   out_5997582763311156755[22] = 0;
   out_5997582763311156755[23] = 0;
   out_5997582763311156755[24] = 0;
   out_5997582763311156755[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5997582763311156755[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_5997582763311156755[27] = 0;
   out_5997582763311156755[28] = 0;
   out_5997582763311156755[29] = 0;
   out_5997582763311156755[30] = 0;
   out_5997582763311156755[31] = 0;
   out_5997582763311156755[32] = 0;
   out_5997582763311156755[33] = 0;
   out_5997582763311156755[34] = 0;
   out_5997582763311156755[35] = 0;
   out_5997582763311156755[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5997582763311156755[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5997582763311156755[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5997582763311156755[39] = 0;
   out_5997582763311156755[40] = 0;
   out_5997582763311156755[41] = 0;
   out_5997582763311156755[42] = 0;
   out_5997582763311156755[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5997582763311156755[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_5997582763311156755[45] = 0;
   out_5997582763311156755[46] = 0;
   out_5997582763311156755[47] = 0;
   out_5997582763311156755[48] = 0;
   out_5997582763311156755[49] = 0;
   out_5997582763311156755[50] = 0;
   out_5997582763311156755[51] = 0;
   out_5997582763311156755[52] = 0;
   out_5997582763311156755[53] = 0;
   out_5997582763311156755[54] = 0;
   out_5997582763311156755[55] = 0;
   out_5997582763311156755[56] = 0;
   out_5997582763311156755[57] = 1;
   out_5997582763311156755[58] = 0;
   out_5997582763311156755[59] = 0;
   out_5997582763311156755[60] = 0;
   out_5997582763311156755[61] = 0;
   out_5997582763311156755[62] = 0;
   out_5997582763311156755[63] = 0;
   out_5997582763311156755[64] = 0;
   out_5997582763311156755[65] = 0;
   out_5997582763311156755[66] = dt;
   out_5997582763311156755[67] = 0;
   out_5997582763311156755[68] = 0;
   out_5997582763311156755[69] = 0;
   out_5997582763311156755[70] = 0;
   out_5997582763311156755[71] = 0;
   out_5997582763311156755[72] = 0;
   out_5997582763311156755[73] = 0;
   out_5997582763311156755[74] = 0;
   out_5997582763311156755[75] = 0;
   out_5997582763311156755[76] = 1;
   out_5997582763311156755[77] = 0;
   out_5997582763311156755[78] = 0;
   out_5997582763311156755[79] = 0;
   out_5997582763311156755[80] = 0;
   out_5997582763311156755[81] = 0;
   out_5997582763311156755[82] = 0;
   out_5997582763311156755[83] = 0;
   out_5997582763311156755[84] = 0;
   out_5997582763311156755[85] = dt;
   out_5997582763311156755[86] = 0;
   out_5997582763311156755[87] = 0;
   out_5997582763311156755[88] = 0;
   out_5997582763311156755[89] = 0;
   out_5997582763311156755[90] = 0;
   out_5997582763311156755[91] = 0;
   out_5997582763311156755[92] = 0;
   out_5997582763311156755[93] = 0;
   out_5997582763311156755[94] = 0;
   out_5997582763311156755[95] = 1;
   out_5997582763311156755[96] = 0;
   out_5997582763311156755[97] = 0;
   out_5997582763311156755[98] = 0;
   out_5997582763311156755[99] = 0;
   out_5997582763311156755[100] = 0;
   out_5997582763311156755[101] = 0;
   out_5997582763311156755[102] = 0;
   out_5997582763311156755[103] = 0;
   out_5997582763311156755[104] = dt;
   out_5997582763311156755[105] = 0;
   out_5997582763311156755[106] = 0;
   out_5997582763311156755[107] = 0;
   out_5997582763311156755[108] = 0;
   out_5997582763311156755[109] = 0;
   out_5997582763311156755[110] = 0;
   out_5997582763311156755[111] = 0;
   out_5997582763311156755[112] = 0;
   out_5997582763311156755[113] = 0;
   out_5997582763311156755[114] = 1;
   out_5997582763311156755[115] = 0;
   out_5997582763311156755[116] = 0;
   out_5997582763311156755[117] = 0;
   out_5997582763311156755[118] = 0;
   out_5997582763311156755[119] = 0;
   out_5997582763311156755[120] = 0;
   out_5997582763311156755[121] = 0;
   out_5997582763311156755[122] = 0;
   out_5997582763311156755[123] = 0;
   out_5997582763311156755[124] = 0;
   out_5997582763311156755[125] = 0;
   out_5997582763311156755[126] = 0;
   out_5997582763311156755[127] = 0;
   out_5997582763311156755[128] = 0;
   out_5997582763311156755[129] = 0;
   out_5997582763311156755[130] = 0;
   out_5997582763311156755[131] = 0;
   out_5997582763311156755[132] = 0;
   out_5997582763311156755[133] = 1;
   out_5997582763311156755[134] = 0;
   out_5997582763311156755[135] = 0;
   out_5997582763311156755[136] = 0;
   out_5997582763311156755[137] = 0;
   out_5997582763311156755[138] = 0;
   out_5997582763311156755[139] = 0;
   out_5997582763311156755[140] = 0;
   out_5997582763311156755[141] = 0;
   out_5997582763311156755[142] = 0;
   out_5997582763311156755[143] = 0;
   out_5997582763311156755[144] = 0;
   out_5997582763311156755[145] = 0;
   out_5997582763311156755[146] = 0;
   out_5997582763311156755[147] = 0;
   out_5997582763311156755[148] = 0;
   out_5997582763311156755[149] = 0;
   out_5997582763311156755[150] = 0;
   out_5997582763311156755[151] = 0;
   out_5997582763311156755[152] = 1;
   out_5997582763311156755[153] = 0;
   out_5997582763311156755[154] = 0;
   out_5997582763311156755[155] = 0;
   out_5997582763311156755[156] = 0;
   out_5997582763311156755[157] = 0;
   out_5997582763311156755[158] = 0;
   out_5997582763311156755[159] = 0;
   out_5997582763311156755[160] = 0;
   out_5997582763311156755[161] = 0;
   out_5997582763311156755[162] = 0;
   out_5997582763311156755[163] = 0;
   out_5997582763311156755[164] = 0;
   out_5997582763311156755[165] = 0;
   out_5997582763311156755[166] = 0;
   out_5997582763311156755[167] = 0;
   out_5997582763311156755[168] = 0;
   out_5997582763311156755[169] = 0;
   out_5997582763311156755[170] = 0;
   out_5997582763311156755[171] = 1;
   out_5997582763311156755[172] = 0;
   out_5997582763311156755[173] = 0;
   out_5997582763311156755[174] = 0;
   out_5997582763311156755[175] = 0;
   out_5997582763311156755[176] = 0;
   out_5997582763311156755[177] = 0;
   out_5997582763311156755[178] = 0;
   out_5997582763311156755[179] = 0;
   out_5997582763311156755[180] = 0;
   out_5997582763311156755[181] = 0;
   out_5997582763311156755[182] = 0;
   out_5997582763311156755[183] = 0;
   out_5997582763311156755[184] = 0;
   out_5997582763311156755[185] = 0;
   out_5997582763311156755[186] = 0;
   out_5997582763311156755[187] = 0;
   out_5997582763311156755[188] = 0;
   out_5997582763311156755[189] = 0;
   out_5997582763311156755[190] = 1;
   out_5997582763311156755[191] = 0;
   out_5997582763311156755[192] = 0;
   out_5997582763311156755[193] = 0;
   out_5997582763311156755[194] = 0;
   out_5997582763311156755[195] = 0;
   out_5997582763311156755[196] = 0;
   out_5997582763311156755[197] = 0;
   out_5997582763311156755[198] = 0;
   out_5997582763311156755[199] = 0;
   out_5997582763311156755[200] = 0;
   out_5997582763311156755[201] = 0;
   out_5997582763311156755[202] = 0;
   out_5997582763311156755[203] = 0;
   out_5997582763311156755[204] = 0;
   out_5997582763311156755[205] = 0;
   out_5997582763311156755[206] = 0;
   out_5997582763311156755[207] = 0;
   out_5997582763311156755[208] = 0;
   out_5997582763311156755[209] = 1;
   out_5997582763311156755[210] = 0;
   out_5997582763311156755[211] = 0;
   out_5997582763311156755[212] = 0;
   out_5997582763311156755[213] = 0;
   out_5997582763311156755[214] = 0;
   out_5997582763311156755[215] = 0;
   out_5997582763311156755[216] = 0;
   out_5997582763311156755[217] = 0;
   out_5997582763311156755[218] = 0;
   out_5997582763311156755[219] = 0;
   out_5997582763311156755[220] = 0;
   out_5997582763311156755[221] = 0;
   out_5997582763311156755[222] = 0;
   out_5997582763311156755[223] = 0;
   out_5997582763311156755[224] = 0;
   out_5997582763311156755[225] = 0;
   out_5997582763311156755[226] = 0;
   out_5997582763311156755[227] = 0;
   out_5997582763311156755[228] = 1;
   out_5997582763311156755[229] = 0;
   out_5997582763311156755[230] = 0;
   out_5997582763311156755[231] = 0;
   out_5997582763311156755[232] = 0;
   out_5997582763311156755[233] = 0;
   out_5997582763311156755[234] = 0;
   out_5997582763311156755[235] = 0;
   out_5997582763311156755[236] = 0;
   out_5997582763311156755[237] = 0;
   out_5997582763311156755[238] = 0;
   out_5997582763311156755[239] = 0;
   out_5997582763311156755[240] = 0;
   out_5997582763311156755[241] = 0;
   out_5997582763311156755[242] = 0;
   out_5997582763311156755[243] = 0;
   out_5997582763311156755[244] = 0;
   out_5997582763311156755[245] = 0;
   out_5997582763311156755[246] = 0;
   out_5997582763311156755[247] = 1;
   out_5997582763311156755[248] = 0;
   out_5997582763311156755[249] = 0;
   out_5997582763311156755[250] = 0;
   out_5997582763311156755[251] = 0;
   out_5997582763311156755[252] = 0;
   out_5997582763311156755[253] = 0;
   out_5997582763311156755[254] = 0;
   out_5997582763311156755[255] = 0;
   out_5997582763311156755[256] = 0;
   out_5997582763311156755[257] = 0;
   out_5997582763311156755[258] = 0;
   out_5997582763311156755[259] = 0;
   out_5997582763311156755[260] = 0;
   out_5997582763311156755[261] = 0;
   out_5997582763311156755[262] = 0;
   out_5997582763311156755[263] = 0;
   out_5997582763311156755[264] = 0;
   out_5997582763311156755[265] = 0;
   out_5997582763311156755[266] = 1;
   out_5997582763311156755[267] = 0;
   out_5997582763311156755[268] = 0;
   out_5997582763311156755[269] = 0;
   out_5997582763311156755[270] = 0;
   out_5997582763311156755[271] = 0;
   out_5997582763311156755[272] = 0;
   out_5997582763311156755[273] = 0;
   out_5997582763311156755[274] = 0;
   out_5997582763311156755[275] = 0;
   out_5997582763311156755[276] = 0;
   out_5997582763311156755[277] = 0;
   out_5997582763311156755[278] = 0;
   out_5997582763311156755[279] = 0;
   out_5997582763311156755[280] = 0;
   out_5997582763311156755[281] = 0;
   out_5997582763311156755[282] = 0;
   out_5997582763311156755[283] = 0;
   out_5997582763311156755[284] = 0;
   out_5997582763311156755[285] = 1;
   out_5997582763311156755[286] = 0;
   out_5997582763311156755[287] = 0;
   out_5997582763311156755[288] = 0;
   out_5997582763311156755[289] = 0;
   out_5997582763311156755[290] = 0;
   out_5997582763311156755[291] = 0;
   out_5997582763311156755[292] = 0;
   out_5997582763311156755[293] = 0;
   out_5997582763311156755[294] = 0;
   out_5997582763311156755[295] = 0;
   out_5997582763311156755[296] = 0;
   out_5997582763311156755[297] = 0;
   out_5997582763311156755[298] = 0;
   out_5997582763311156755[299] = 0;
   out_5997582763311156755[300] = 0;
   out_5997582763311156755[301] = 0;
   out_5997582763311156755[302] = 0;
   out_5997582763311156755[303] = 0;
   out_5997582763311156755[304] = 1;
   out_5997582763311156755[305] = 0;
   out_5997582763311156755[306] = 0;
   out_5997582763311156755[307] = 0;
   out_5997582763311156755[308] = 0;
   out_5997582763311156755[309] = 0;
   out_5997582763311156755[310] = 0;
   out_5997582763311156755[311] = 0;
   out_5997582763311156755[312] = 0;
   out_5997582763311156755[313] = 0;
   out_5997582763311156755[314] = 0;
   out_5997582763311156755[315] = 0;
   out_5997582763311156755[316] = 0;
   out_5997582763311156755[317] = 0;
   out_5997582763311156755[318] = 0;
   out_5997582763311156755[319] = 0;
   out_5997582763311156755[320] = 0;
   out_5997582763311156755[321] = 0;
   out_5997582763311156755[322] = 0;
   out_5997582763311156755[323] = 1;
}
void h_4(double *state, double *unused, double *out_3040948559389363640) {
   out_3040948559389363640[0] = state[6] + state[9];
   out_3040948559389363640[1] = state[7] + state[10];
   out_3040948559389363640[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_7515212026822338225) {
   out_7515212026822338225[0] = 0;
   out_7515212026822338225[1] = 0;
   out_7515212026822338225[2] = 0;
   out_7515212026822338225[3] = 0;
   out_7515212026822338225[4] = 0;
   out_7515212026822338225[5] = 0;
   out_7515212026822338225[6] = 1;
   out_7515212026822338225[7] = 0;
   out_7515212026822338225[8] = 0;
   out_7515212026822338225[9] = 1;
   out_7515212026822338225[10] = 0;
   out_7515212026822338225[11] = 0;
   out_7515212026822338225[12] = 0;
   out_7515212026822338225[13] = 0;
   out_7515212026822338225[14] = 0;
   out_7515212026822338225[15] = 0;
   out_7515212026822338225[16] = 0;
   out_7515212026822338225[17] = 0;
   out_7515212026822338225[18] = 0;
   out_7515212026822338225[19] = 0;
   out_7515212026822338225[20] = 0;
   out_7515212026822338225[21] = 0;
   out_7515212026822338225[22] = 0;
   out_7515212026822338225[23] = 0;
   out_7515212026822338225[24] = 0;
   out_7515212026822338225[25] = 1;
   out_7515212026822338225[26] = 0;
   out_7515212026822338225[27] = 0;
   out_7515212026822338225[28] = 1;
   out_7515212026822338225[29] = 0;
   out_7515212026822338225[30] = 0;
   out_7515212026822338225[31] = 0;
   out_7515212026822338225[32] = 0;
   out_7515212026822338225[33] = 0;
   out_7515212026822338225[34] = 0;
   out_7515212026822338225[35] = 0;
   out_7515212026822338225[36] = 0;
   out_7515212026822338225[37] = 0;
   out_7515212026822338225[38] = 0;
   out_7515212026822338225[39] = 0;
   out_7515212026822338225[40] = 0;
   out_7515212026822338225[41] = 0;
   out_7515212026822338225[42] = 0;
   out_7515212026822338225[43] = 0;
   out_7515212026822338225[44] = 1;
   out_7515212026822338225[45] = 0;
   out_7515212026822338225[46] = 0;
   out_7515212026822338225[47] = 1;
   out_7515212026822338225[48] = 0;
   out_7515212026822338225[49] = 0;
   out_7515212026822338225[50] = 0;
   out_7515212026822338225[51] = 0;
   out_7515212026822338225[52] = 0;
   out_7515212026822338225[53] = 0;
}
void h_10(double *state, double *unused, double *out_2024725912263715489) {
   out_2024725912263715489[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2024725912263715489[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2024725912263715489[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_7567938388907257562) {
   out_7567938388907257562[0] = 0;
   out_7567938388907257562[1] = 9.8100000000000005*cos(state[1]);
   out_7567938388907257562[2] = 0;
   out_7567938388907257562[3] = 0;
   out_7567938388907257562[4] = -state[8];
   out_7567938388907257562[5] = state[7];
   out_7567938388907257562[6] = 0;
   out_7567938388907257562[7] = state[5];
   out_7567938388907257562[8] = -state[4];
   out_7567938388907257562[9] = 0;
   out_7567938388907257562[10] = 0;
   out_7567938388907257562[11] = 0;
   out_7567938388907257562[12] = 1;
   out_7567938388907257562[13] = 0;
   out_7567938388907257562[14] = 0;
   out_7567938388907257562[15] = 1;
   out_7567938388907257562[16] = 0;
   out_7567938388907257562[17] = 0;
   out_7567938388907257562[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_7567938388907257562[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_7567938388907257562[20] = 0;
   out_7567938388907257562[21] = state[8];
   out_7567938388907257562[22] = 0;
   out_7567938388907257562[23] = -state[6];
   out_7567938388907257562[24] = -state[5];
   out_7567938388907257562[25] = 0;
   out_7567938388907257562[26] = state[3];
   out_7567938388907257562[27] = 0;
   out_7567938388907257562[28] = 0;
   out_7567938388907257562[29] = 0;
   out_7567938388907257562[30] = 0;
   out_7567938388907257562[31] = 1;
   out_7567938388907257562[32] = 0;
   out_7567938388907257562[33] = 0;
   out_7567938388907257562[34] = 1;
   out_7567938388907257562[35] = 0;
   out_7567938388907257562[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_7567938388907257562[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_7567938388907257562[38] = 0;
   out_7567938388907257562[39] = -state[7];
   out_7567938388907257562[40] = state[6];
   out_7567938388907257562[41] = 0;
   out_7567938388907257562[42] = state[4];
   out_7567938388907257562[43] = -state[3];
   out_7567938388907257562[44] = 0;
   out_7567938388907257562[45] = 0;
   out_7567938388907257562[46] = 0;
   out_7567938388907257562[47] = 0;
   out_7567938388907257562[48] = 0;
   out_7567938388907257562[49] = 0;
   out_7567938388907257562[50] = 1;
   out_7567938388907257562[51] = 0;
   out_7567938388907257562[52] = 0;
   out_7567938388907257562[53] = 1;
}
void h_13(double *state, double *unused, double *out_8096238294370646169) {
   out_8096238294370646169[0] = state[3];
   out_8096238294370646169[1] = state[4];
   out_8096238294370646169[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3320900838570512462) {
   out_3320900838570512462[0] = 0;
   out_3320900838570512462[1] = 0;
   out_3320900838570512462[2] = 0;
   out_3320900838570512462[3] = 1;
   out_3320900838570512462[4] = 0;
   out_3320900838570512462[5] = 0;
   out_3320900838570512462[6] = 0;
   out_3320900838570512462[7] = 0;
   out_3320900838570512462[8] = 0;
   out_3320900838570512462[9] = 0;
   out_3320900838570512462[10] = 0;
   out_3320900838570512462[11] = 0;
   out_3320900838570512462[12] = 0;
   out_3320900838570512462[13] = 0;
   out_3320900838570512462[14] = 0;
   out_3320900838570512462[15] = 0;
   out_3320900838570512462[16] = 0;
   out_3320900838570512462[17] = 0;
   out_3320900838570512462[18] = 0;
   out_3320900838570512462[19] = 0;
   out_3320900838570512462[20] = 0;
   out_3320900838570512462[21] = 0;
   out_3320900838570512462[22] = 1;
   out_3320900838570512462[23] = 0;
   out_3320900838570512462[24] = 0;
   out_3320900838570512462[25] = 0;
   out_3320900838570512462[26] = 0;
   out_3320900838570512462[27] = 0;
   out_3320900838570512462[28] = 0;
   out_3320900838570512462[29] = 0;
   out_3320900838570512462[30] = 0;
   out_3320900838570512462[31] = 0;
   out_3320900838570512462[32] = 0;
   out_3320900838570512462[33] = 0;
   out_3320900838570512462[34] = 0;
   out_3320900838570512462[35] = 0;
   out_3320900838570512462[36] = 0;
   out_3320900838570512462[37] = 0;
   out_3320900838570512462[38] = 0;
   out_3320900838570512462[39] = 0;
   out_3320900838570512462[40] = 0;
   out_3320900838570512462[41] = 1;
   out_3320900838570512462[42] = 0;
   out_3320900838570512462[43] = 0;
   out_3320900838570512462[44] = 0;
   out_3320900838570512462[45] = 0;
   out_3320900838570512462[46] = 0;
   out_3320900838570512462[47] = 0;
   out_3320900838570512462[48] = 0;
   out_3320900838570512462[49] = 0;
   out_3320900838570512462[50] = 0;
   out_3320900838570512462[51] = 0;
   out_3320900838570512462[52] = 0;
   out_3320900838570512462[53] = 0;
}
void h_14(double *state, double *unused, double *out_9101361896854545328) {
   out_9101361896854545328[0] = state[6];
   out_9101361896854545328[1] = state[7];
   out_9101361896854545328[2] = state[8];
}
void H_14(double *state, double *unused, double *out_4432423594526965929) {
   out_4432423594526965929[0] = 0;
   out_4432423594526965929[1] = 0;
   out_4432423594526965929[2] = 0;
   out_4432423594526965929[3] = 0;
   out_4432423594526965929[4] = 0;
   out_4432423594526965929[5] = 0;
   out_4432423594526965929[6] = 1;
   out_4432423594526965929[7] = 0;
   out_4432423594526965929[8] = 0;
   out_4432423594526965929[9] = 0;
   out_4432423594526965929[10] = 0;
   out_4432423594526965929[11] = 0;
   out_4432423594526965929[12] = 0;
   out_4432423594526965929[13] = 0;
   out_4432423594526965929[14] = 0;
   out_4432423594526965929[15] = 0;
   out_4432423594526965929[16] = 0;
   out_4432423594526965929[17] = 0;
   out_4432423594526965929[18] = 0;
   out_4432423594526965929[19] = 0;
   out_4432423594526965929[20] = 0;
   out_4432423594526965929[21] = 0;
   out_4432423594526965929[22] = 0;
   out_4432423594526965929[23] = 0;
   out_4432423594526965929[24] = 0;
   out_4432423594526965929[25] = 1;
   out_4432423594526965929[26] = 0;
   out_4432423594526965929[27] = 0;
   out_4432423594526965929[28] = 0;
   out_4432423594526965929[29] = 0;
   out_4432423594526965929[30] = 0;
   out_4432423594526965929[31] = 0;
   out_4432423594526965929[32] = 0;
   out_4432423594526965929[33] = 0;
   out_4432423594526965929[34] = 0;
   out_4432423594526965929[35] = 0;
   out_4432423594526965929[36] = 0;
   out_4432423594526965929[37] = 0;
   out_4432423594526965929[38] = 0;
   out_4432423594526965929[39] = 0;
   out_4432423594526965929[40] = 0;
   out_4432423594526965929[41] = 0;
   out_4432423594526965929[42] = 0;
   out_4432423594526965929[43] = 0;
   out_4432423594526965929[44] = 1;
   out_4432423594526965929[45] = 0;
   out_4432423594526965929[46] = 0;
   out_4432423594526965929[47] = 0;
   out_4432423594526965929[48] = 0;
   out_4432423594526965929[49] = 0;
   out_4432423594526965929[50] = 0;
   out_4432423594526965929[51] = 0;
   out_4432423594526965929[52] = 0;
   out_4432423594526965929[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_3592422939216669323) {
  err_fun(nom_x, delta_x, out_3592422939216669323);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6915701396310957140) {
  inv_err_fun(nom_x, true_x, out_6915701396310957140);
}
void pose_H_mod_fun(double *state, double *out_3743404816978430653) {
  H_mod_fun(state, out_3743404816978430653);
}
void pose_f_fun(double *state, double dt, double *out_971936760635752887) {
  f_fun(state,  dt, out_971936760635752887);
}
void pose_F_fun(double *state, double dt, double *out_5997582763311156755) {
  F_fun(state,  dt, out_5997582763311156755);
}
void pose_h_4(double *state, double *unused, double *out_3040948559389363640) {
  h_4(state, unused, out_3040948559389363640);
}
void pose_H_4(double *state, double *unused, double *out_7515212026822338225) {
  H_4(state, unused, out_7515212026822338225);
}
void pose_h_10(double *state, double *unused, double *out_2024725912263715489) {
  h_10(state, unused, out_2024725912263715489);
}
void pose_H_10(double *state, double *unused, double *out_7567938388907257562) {
  H_10(state, unused, out_7567938388907257562);
}
void pose_h_13(double *state, double *unused, double *out_8096238294370646169) {
  h_13(state, unused, out_8096238294370646169);
}
void pose_H_13(double *state, double *unused, double *out_3320900838570512462) {
  H_13(state, unused, out_3320900838570512462);
}
void pose_h_14(double *state, double *unused, double *out_9101361896854545328) {
  h_14(state, unused, out_9101361896854545328);
}
void pose_H_14(double *state, double *unused, double *out_4432423594526965929) {
  H_14(state, unused, out_4432423594526965929);
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
